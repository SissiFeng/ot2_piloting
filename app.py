import gradio as gr
from queue import Queue
import threading
import time
import paho.mqtt.client as mqtt
import json
import secrets
from well_status_utils import find_unused_wells, update_used_wells



import os

MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD")
print(f"MONGODB_PASSWORD: {MONGODB_PASSWORD}")
blinded_connection_string = os.getenv("blinded_connection_string")
print(f"blinded_connection_string: {blinded_connection_string}")
connection_string = blinded_connection_string.replace("<db_password>", MONGODB_PASSWORD)
print(f"Connection String: {connection_string}")

# Task Queue
task_queue = Queue()
result_queue = Queue()
current_task = None

# MQTT Configuration
MQTT_BROKER = "248cc294c37642359297f75b7b023374.s2.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USERNAME = "sgbaird"
MQTT_PASSWORD = "D.Pq5gYtejYbU#L"


OT2_SERIAL = "OT2CEP20240218R04"
PICO_ID = "e66130100f895134"

OT2_COMMAND_TOPIC = f"command/ot2/{OT2_SERIAL}/pipette"
OT2_STATUS_TOPIC = f"status/ot2/{OT2_SERIAL}/complete"
SENSOR_COMMAND_TOPIC = f"command/picow/{PICO_ID}/as7341/read"
SENSOR_DATA_TOPIC = f"color-mixing/picow/{PICO_ID}/as7341"


# MQTT Client
mqtt_client = mqtt.Client()
mqtt_client.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLS_CLIENT)  # Enable TLS
mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

# MQTT Handlers
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT Broker with result code", rc)
    client.subscribe([(OT2_STATUS_TOPIC,2),(SENSOR_DATA_TOPIC,2)])

def on_message(client, userdata, msg):
    global current_task
    global sensor_results

    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        if msg.topic == OT2_STATUS_TOPIC:
            handle_sensor_status(payload)

        elif msg.topic == SENSOR_DATA_TOPIC:
            print("Sensor: Data received.")
            print(payload)
            sensor_results = payload
            mqtt_client.publish(
                OT2_COMMAND_TOPIC,
                json.dumps({"command": {"sensor_status": "read"}, "experiment_id": payload["experiment_id"],"session_id": payload["session_id"]}),
            )
            print("Sending sensor to charging position.")

    except Exception as e:
        print("Error processing MQTT message:", e)

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
mqtt_client.loop_start()

# Task processing logic
def add_to_queue(student_id, R, Y, B):
    global current_task

    # Ensure total volume is 300 µL
    if R + Y + B != 300:
        raise gr.Error("The total R, Y, and B volume must be exactly 300 µL.")
        return
    
    experiment_id = secrets.token_hex(4) 

    try:
        # Find an available well on the plate
        empty_wells = find_unused_wells()
        if not empty_wells:
            raise ValueError("No available wells for the experiment.")
        selected_well = empty_wells[0]
        # Execute OT-2 protocol to mix the RYB proportions
        update_used_wells([selected_well])  # Mark the well as used

    except Exception as e:
        yield {
        "Status": "Error",
        "Message": f"Experiment execution failed: {e}"
        }
        return 
    
    # Add task to queue
    task = {
        "R": R,
        "Y": Y,
        "B": B,
        "well":selected_well,
        "session_id": student_id,
        "experiment_id": experiment_id,
        "status": "queued",
    }
    task_queue.put(task)

    # Monitor queue position
    while task in list(task_queue.queue):
        queue_position = list(task_queue.queue).index(task) + 1
        time.sleep(1)  # Simulate periodic updates
        yield {
            "Status": "Queued",
            "Message": f"Your experiment is queued. Current position: {queue_position}",
            "Student ID": student_id,
            "RYB Volumes (µL)": {"R": R, "Y": Y, "B": B},
            "well":selected_well,
        }
    
    # When processing starts
    yield {"Status": "In Progress", "Message": "Experiment is running..."}  
      
    while True:
        result = result_queue.get()  # This will block until the result is available
        if result["Experiment ID"] == experiment_id:
            yield result # Return the updated result to the Gradio interface
            break

# Start Task Processor Thread
def task_processor():
    global current_task
    while True:
        if not current_task and not task_queue.empty():
            current_task = task_queue.get()
            current_task["status"] = "processing"
            mqtt_client.publish(
                OT2_COMMAND_TOPIC,
                json.dumps({
                    "command": {"R": current_task["R"], "Y": current_task["Y"], "B": current_task["B"], "well": current_task["well"]}, "experiment_id": current_task["experiment_id"],
                    "session_id": current_task["session_id"]
                }),
            )
        time.sleep(1)

def handle_sensor_status(payload):
    global current_task
    global sensor_results
    if "in_place" in json.dumps(payload):
        print("OT-2: Sensor in place. Sending read command to sensor.")
        mqtt_client.publish(SENSOR_COMMAND_TOPIC,
                    json.dumps({
                        "command": {
                            "R": current_task["R"],
                            "Y": current_task["Y"],
                            "B": current_task["B"],
                            "well": current_task["well"]
                        },
                        "experiment_id": current_task["experiment_id"],
                        "session_id": current_task["session_id"]
                    })
                )

    elif payload["status"]["sensor_status"] == "charging":
            print("OT-2: Sensor returned to charging position.")
            # Push result to result_queue
            result_queue.put({
                    "Message": "Experiment completed!",
                    "Student ID": current_task["session_id"],
                    "Command": {
                        "R": current_task["R"], 
                        "Y": current_task["Y"],
                        "B": current_task["B"],
                        "well": current_task["well"],
                    },
                    "Sensor Data": sensor_results["sensor_data"],
                    "Experiment ID": current_task["experiment_id"]
                    
               })
            
            current_task = None

 

processor_thread = threading.Thread(target=task_processor, daemon=True)
processor_thread.start()

# Define the Gradio interface
inputs = [
    gr.Textbox(label="Student ID", placeholder="Enter your unique ID"),
    gr.Slider(1, 300, step=1, label="Red (R) Volume (µL)"),
    gr.Slider(1, 300, step=1, label="Yellow (Y) Volume (µL)"),
    gr.Slider(1, 300, step=1, label="Blue (B) Volume (µL)")
]
outputs = gr.JSON()

app = gr.Interface(
    fn=add_to_queue,
    inputs=inputs,
    outputs=outputs,
    title="OT-2 Liquid Color Matching Experiment Queue",
    description="Enter R, Y, and B volumes (in µL). Ensure the total volume is exactly 300 µL.",
    flagging_mode="never"
)

app.launch()
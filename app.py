import gradio as gr
from queue import Queue
import threading
import time
import paho.mqtt.client as mqtt
import json
import secrets
from DB_utls import find_unused_wells, update_used_wells, save_result, get_student_quota, decrement_student_quota


# NOTE: New global dict to store tasks keyed by (student_id, experiment_id)
tasks_dict = {}

task_queue = Queue()
result_queue = Queue()
current_task = None
sensor_results = None
queue_counter = task_queue.qsize()

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


def check_student_quota(student_id):
    """Check student's remaining experiment quota"""
    student_quota = get_student_quota(student_id)
    return student_quota 

def validate_ryb_input(R, Y, B):
    """Validate RYB input volumes"""
    total = R + Y + B
    if total > 300:
        return {
            "is_valid": False, 
            "message": f"Total volume cannot exceed 300 µL. Current total: {total} µL."
        }
    return {
        "is_valid": True, 
        "message": f"Current total: {total} µL."
    }


mqtt_client = mqtt.Client()
mqtt_client.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLS_CLIENT)
mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT Broker with result code {rc}")
    client.subscribe([(OT2_STATUS_TOPIC, 2), (SENSOR_DATA_TOPIC, 2)])

def on_message(client, userdata, msg):
    global current_task, sensor_results
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        if msg.topic == OT2_STATUS_TOPIC:
            handle_sensor_status(payload)
        elif msg.topic == SENSOR_DATA_TOPIC:
            print("Sensor data received")
            sensor_results = payload
            mqtt_client.publish(
                OT2_COMMAND_TOPIC,
                json.dumps({
                    "command": {"sensor_status": "read"},
                    "experiment_id": payload["experiment_id"],
                    "session_id": payload["session_id"]
                }),
            )
    except Exception as e:
        print(f"Error processing MQTT message: {e}")

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
mqtt_client.loop_start()

def handle_sensor_status(payload):
    global current_task, sensor_results
    if "in_place" in json.dumps(payload):
        mqtt_client.publish(
            SENSOR_COMMAND_TOPIC,
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
        
        experiment_result = {
        "Status": "Complete",
        "Message": "Experiment completed successfully!",
        "Student ID": current_task["session_id"],
        "Command": {
            "R": current_task["R"],
            "Y": current_task["Y"],
            "B": current_task["B"],
            "well": current_task["well"],
        },
        "Sensor Data": sensor_results["sensor_data"],
        "Experiment ID": current_task["experiment_id"]
    }
    # Store full result in result queue
        result_queue.put(experiment_result)

    # Create a version of experiment_result without "Status" and "Message" for database storage
        db_data = {key: experiment_result[key] for key in experiment_result if key not in ["Status", "Message"]}

        save_result(db_data)

        current_task = None


def task_processor():
    """
    Background thread that processes tasks one by one.
    """
    global current_task, queue_counter
    task_start_time = None
    TIMEOUT_SECONDS = 165  # 2min45s
    
    while True:
        if current_task:
            # Check for timeout
            if task_start_time and (time.time() - task_start_time > TIMEOUT_SECONDS):
                print("sending timeout message to OT-2")
                mqtt_client.publish(
                    OT2_COMMAND_TOPIC,
                    json.dumps({
                        "command": {"sensor_status": "sensor_timeout"},
                        "experiment_id": current_task["experiment_id"],
                        "session_id": current_task["session_id"]
                    }),
                ) 
                result_queue.put({
                    "Status": "Error",
                    "Message": "Experiment timed out",
                    "Student ID": current_task["session_id"],
                    "Command": {
                        "R": current_task["R"],
                        "Y": current_task["Y"],
                        "B": current_task["B"],
                        "well": current_task["well"],
                    },
                    "Experiment ID": current_task["experiment_id"]
                })
                current_task = None
                task_start_time = None
                continue

        if not current_task and not task_queue.empty():
            # Fetch a new task from the queue
            student_id, experiment_id = task_queue.get()  # NOTE: We'll store (student_id, experiment_id) instead of task
            queue_counter -= 1
            task_start_time = time.time()

            # NOTE: We retrieve the actual task from tasks_dict
            current_task = tasks_dict[(student_id, experiment_id)]

            print(f"[DEBUG] Task processor - Getting new task. Queue counter: {queue_counter}")
           
            print(f"[DEBUG] Task start time: {task_start_time}")
            
            # Mark status as "processing"
            current_task["status"] = "processing"
            
            mqtt_client.publish(
                OT2_COMMAND_TOPIC,
                json.dumps({
                    "command": {
                        "R": current_task["R"],
                        "Y": current_task["Y"],
                        "B": current_task["B"],
                        "well": current_task["well"]
                    },
                    "experiment_id": current_task["experiment_id"],
                    "session_id": current_task["session_id"]
                }),
            )
        
        time.sleep(1)


processor_thread = threading.Thread(target=task_processor, daemon=True)
processor_thread.start()


def verify_student_id(student_id):
    """Verify student ID and check quota"""
    global queue_counter
    if not student_id:
        return [
            gr.update(interactive=False, value=1),
            gr.update(interactive=False, value=1),
            gr.update(interactive=False, value=1),
            "Please enter a Student ID",
            gr.update(interactive=False)
        ]
    
    quota_remaining = check_student_quota(student_id)
    
    print(f"[DEBUG] Updating status:  Queue counter: {queue_counter}")
    
    if quota_remaining <= 0:
        return [
            gr.update(interactive=False, value=1),
            gr.update(interactive=False, value=1),
            gr.update(interactive=False, value=1),
            "No experiments remaining. Please contact administrator.",
            gr.update(interactive=False)
        ]
    
    return [
        gr.update(interactive=True, value=1),
        gr.update(interactive=True, value=1),
        gr.update(interactive=True, value=1),
        f"Student ID verified. Available experiments: {quota_remaining}\nCurrent queue length: {queue_counter} experiment(s)",
        gr.update(interactive=True)
    ]

def update_status_with_queue(R, Y, B):
    """Check if RYB inputs are valid and return updated queue info"""
    global queue_counter
    validation_result = validate_ryb_input(R, Y, B)
    total = R + Y + B
    return [
        f"{validation_result['message']}\nCurrent queue length: {queue_counter} experiment(s)",
        gr.update(interactive=(total <= 300))
    ]

def update_queue_display():
    """Refresh queue info for the UI"""
    global current_task, queue_counter
    try:
        print(f"[DEBUG] Updating queue display - Counter: {queue_counter}")
        print(f"[DEBUG] Current task: {current_task}")
        
        if current_task:
            status = f"""### Current Queue Status
- Active experiment: Yes
- Queue length: {queue_counter} experiment(s)"""
        else:
            status = f"""### Current Queue Status
- Active experiment: No
- Queue length: {queue_counter} experiment(s)
- Total experiments: {queue_counter}"""
        return status
    except Exception as e:
        print(f"[DEBUG] Error in update_queue_display: {str(e)}")
        return f"Error getting queue status: {str(e)}"


def add_to_queue(student_id, R, Y, B):
    global queue_counter
    print(f"[DEBUG] Before adding - Queue counter: {queue_counter}")
    
    # Validate RYB inputs
    validation_result = validate_ryb_input(R, Y, B)
    if not validation_result["is_valid"]:
        yield {
            "Status": "Error", 
            "Message": validation_result["message"]
        }
        return
    
    # Check quota
    quota_remaining = check_student_quota(student_id)
    if quota_remaining <= 0:
        yield {
            "Status": "Error", 
            "Message": "No experiments remaining"
        }
        return
    
    # Select well
    experiment_id = secrets.token_hex(4)
    try:
        empty_wells = find_unused_wells()
        if not empty_wells:
            raise ValueError("No available wells")
        selected_well = empty_wells[0]
        

    except Exception as e:
        yield {
            "Status": "Error", 
            "Message": str(e)
        }
        return
    
    # NOTE: Create the task and store it in tasks_dict
    task = {
        "R": R,
        "Y": Y,
        "B": B,
        "well": selected_well,
        "session_id": student_id,
        "experiment_id": experiment_id,
        "status": "queued",
    }
    tasks_dict[(student_id, experiment_id)] = task  # Keep track globally
    
    # Put only (student_id, experiment_id) in the Queue
    task_queue.put((student_id, experiment_id))
    queue_counter += 1
    update_used_wells([selected_well])
    decrement_student_quota(student_id)

    print(f"[DEBUG] After adding - Queue counter: {queue_counter}")
    print(f"DEBUG: Current queue content: {[t for t in list(task_queue.queue)]}")
    print(f"[DEBUG] Task added: {task}")
    
    # First yield: "Queued"
    yield {
        "Status": "Queued",
        "Position": queue_counter,
        "Student ID": student_id,
        "Experiment ID": experiment_id,
        "Well": selected_well,
        "Volumes": {"R": R, "Y": Y, "B": B}
    }
    
    # NOTE: Wait until the task's status becomes 'processing'
    #       This ensures we only yield "Running" when the backend actually starts the job.
    while tasks_dict[(student_id, experiment_id)]["status"] == "queued":
        time.sleep(15)
    
    # Second yield: "Running" (happens only after status is 'processing')
    yield {
        "Status": "Running",
        "Student ID": student_id,
        "Experiment ID": experiment_id,
        "Well": selected_well,
        "Volumes": {"R": R, "Y": Y, "B": B}
    }

    # Finally, wait for the result
    result = result_queue.get()
    yield result


with gr.Blocks(title="OT-2 Liquid Color Matching Experiment Queue") as demo:
    gr.Markdown("## OT-2 Liquid Color Matching Experiment Queue")
    gr.Markdown("Enter R, Y, and B volumes (in µL). Total volume must be exactly 300 µL.")
    
    with gr.Row():
        with gr.Column(scale=2):
            with gr.Row():
                student_id_input = gr.Textbox(
                    label="Student ID",
                    placeholder="Enter your unique ID"
                )
                verify_id_btn = gr.Button("Verify ID")
            
            r_slider = gr.Slider(1, 300, step=1, label="Red (R) Volume (µL)", interactive=False)
            y_slider = gr.Slider(1, 300, step=1, label="Yellow (Y) Volume (µL)", interactive=False)
            b_slider = gr.Slider(1, 300, step=1, label="Blue (B) Volume (µL)", interactive=False)
            status_output = gr.Textbox(label="Status")
            submit_btn = gr.Button("Submit Experiment", interactive=False)
            result_output = gr.JSON(label="Experiment Status")
        
        with gr.Column(scale=1):
            gr.Markdown("### Queue Status")
            queue_status = gr.Markdown("Loading queue status...")
            update_status_btn = gr.Button("Refresh Queue Status")

    verify_id_btn.click(
        verify_student_id,
        inputs=[student_id_input],
        outputs=[r_slider, y_slider, b_slider, status_output, submit_btn],
        api_name="verify_student_id"  
    )

    r_slider.change(
        update_status_with_queue, 
        inputs=[r_slider, y_slider, b_slider], 
        outputs=[status_output, submit_btn]
    )
    y_slider.change(
        update_status_with_queue, 
        inputs=[r_slider, y_slider, b_slider], 
        outputs=[status_output, submit_btn]
    )
    b_slider.change(
        update_status_with_queue, 
        inputs=[r_slider, y_slider, b_slider], 
        outputs=[status_output, submit_btn]
    )
    
    # NOTE: concurrency_limit=3 is preserved; no changes here
    submit_btn.click(
        add_to_queue,
        inputs=[student_id_input, r_slider, y_slider, b_slider],
        outputs=result_output,
        api_name="submit",
        concurrency_limit=3
    ).then(
        update_queue_display,
        None,
        queue_status
    )

    update_status_btn.click(
        update_queue_display,
        None,
        queue_status
    )

    demo.load(
        update_queue_display,
        None,
        queue_status
    )

# NOTE: Left as-is, you have not used demo.queue(...) except for concurrency_limit on the .click
demo.queue  # No changes here

if __name__ == "__main__":
    demo.launch()
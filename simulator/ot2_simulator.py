import json
import time
import paho.mqtt.client as mqtt
import os
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Get configuration from environment variables
MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

if not all([MQTT_BROKER, MQTT_USERNAME, MQTT_PASSWORD]):
    raise ValueError("Missing required MQTT environment variables")

# Topics
OT2_STATUS_TOPIC = "status/ot2OT2CEP20240218R0/complete"
SENSOR_DATA_TOPIC = "color-mixing/picow/e66130100f89513/as7341"
SENSOR_COMMAND_TOPIC = "command/picow/e66130100f89513/as7341/read"

class OT2Simulator:
    def __init__(self):
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLS_CLIENT)
        self.mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect

    def on_connect(self, client, userdata, flags, rc):
        logger.info(f"Connected with result code {rc}")
        client.subscribe(SENSOR_COMMAND_TOPIC)

    def on_disconnect(self, client, userdata, rc):
        logger.warning(f"Disconnected with result code {rc}")
        time.sleep(5)
        self.connect()

    def send_ot2_status(self, sensor_status, session_id):
        payload = {
            "status": {"sensor_status": sensor_status},
            "session_id": session_id,
            "timestamp": time.time()
        }
        self.mqtt_client.publish(OT2_STATUS_TOPIC, json.dumps(payload))
        logger.debug(f"OT-2 status sent: {payload}")

    def send_sensor_data(self, sensor_data, session_id):
        payload = {
            "sensor_data": sensor_data,
            "session_id": session_id,
            "timestamp": time.time()
        }
        self.mqtt_client.publish(SENSOR_DATA_TOPIC, json.dumps(payload))
        logger.debug(f"Sensor data sent: {payload}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            logger.debug(f"Received message on topic {msg.topic}: {payload}")

            if msg.topic == SENSOR_COMMAND_TOPIC:
                logger.debug("Simulating sensor read command.")
                time.sleep(2)  # Simulate sensor read delay
                sensor_data = {
                    "ch410": 100,
                    "ch440": 200,
                    "ch470": 300,
                    "ch510": 400,
                    "ch550": 500,
                    "ch583": 600,
                    "ch620": 700,
                    "ch670": 800
                }
                self.send_sensor_data(sensor_data, payload.get("session_id", "unknown"))

        except Exception as e:
            logger.error(f"Error in on_message: {e}", exc_info=True)

    def connect(self):
        try:
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
            self.mqtt_client.loop_start()
        except Exception as e:
            logger.error(f"Connection error: {e}", exc_info=True)
            time.sleep(5)
            self.connect()

    def run(self):
        self.connect()
        session_id = "test_session_1"

        while True:
            try:
                # Simulate OT-2 status updates
                self.send_ot2_status("in_place", session_id)
                time.sleep(5)

                self.send_ot2_status("charging", session_id)
                time.sleep(10)

            except Exception as e:
                logger.error(f"Error in run loop: {e}", exc_info=True)
                time.sleep(5)

if __name__ == "__main__":
    simulator = OT2Simulator()
    simulator.run()

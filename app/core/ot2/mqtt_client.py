import json
import paho.mqtt.client as mqtt
from typing import Callable
import logging

logger = logging.getLogger(__name__)

class OT2MQTTClient:
    def __init__(self, broker, port, username, password, 
                 on_status_callback: Callable = None,
                 on_sensor_data_callback: Callable = None):
        self.client = mqtt.Client()
        self.client.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLS_CLIENT)
        self.client.username_pw_set(username, password)
        
        self.broker = broker
        self.port = port
        self.on_status_callback = on_status_callback
        self.on_sensor_data_callback = on_sensor_data_callback
        
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
    def connect(self):
        self.client.connect(self.broker, self.port)
        self.client.loop_start()
        
    def on_connect(self, client, userdata, flags, rc):
        logger.info(f"Connected with result code {rc}")
        # 订阅相关主题
        client.subscribe("status/ot2OT2CEP20240218R0/complete")
        client.subscribe("color-mixing/picow/e66130100f89513/as7341")
        
    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            
            if msg.topic.startswith("status/"):
                if self.on_status_callback:
                    self.on_status_callback(payload)
                    
            elif msg.topic.startswith("color-mixing/"):
                if self.on_sensor_data_callback:
                    self.on_sensor_data_callback(payload)
                    
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

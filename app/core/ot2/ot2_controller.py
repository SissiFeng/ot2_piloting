import logging
from typing import Dict, Any, Optional
import asyncio
import json
import paho.mqtt.client as mqtt
from datetime import datetime

from ..interfaces.experiment_controller import IExperimentController
from ..config.ot2_config import OT2Config

logger = logging.getLogger(__name__)

class OT2Controller(IExperimentController):
    """OT2 controller implementation using simulator."""
    
    def __init__(self):
        self.mqtt_client = None
        self.config = None
        self.status = "idle"
        self.current_operation = None
        self.session_id = None
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize OT2 controller with MQTT connection."""
        try:
            logger.info("Initializing OT2 controller")
            self.config = OT2Config(**config)
            
            # Setup MQTT client
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLS_CLIENT)
            self.mqtt_client.username_pw_set(
                self.config.hardware.mqtt_username,
                self.config.hardware.mqtt_password
            )
            
            # Connect to MQTT broker
            self.mqtt_client.connect(
                self.config.hardware.mqtt_broker,
                self.config.hardware.mqtt_port
            )
            self.mqtt_client.loop_start()
            
            self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.status = "initialized"
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize OT2 controller: {str(e)}")
            return False
    
    async def run_experiment(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run color mixing experiment with given parameters."""
        try:
            logger.info(f"Running experiment with parameters: {params}")
            self.status = "running"
            self.current_operation = params
            
            # Simulate pipetting operations
            volumes = params.get("volumes", {})
            for color, volume in volumes.items():
                # Simulate picking up tip
                await asyncio.sleep(1)
                logger.info(f"Picked up tip for {color}")
                
                # Simulate aspirating
                await asyncio.sleep(1)
                logger.info(f"Aspirated {volume}µL of {color}")
                
                # Simulate dispensing
                await asyncio.sleep(1)
                logger.info(f"Dispensed {volume}µL of {color}")
                
                # Simulate dropping tip
                await asyncio.sleep(1)
                logger.info(f"Dropped tip")
            
            # Simulate mixing
            await asyncio.sleep(2)
            logger.info("Mixing completed")
            
            # Prepare result
            result = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id,
                "parameters": params,
                "operations_completed": True
            }
            
            self.status = "idle"
            self.current_operation = None
            return result
            
        except Exception as e:
            logger.error(f"Experiment failed: {str(e)}")
            self.status = "error"
            raise
    
    async def stop_experiment(self) -> bool:
        """Stop current experiment."""
        try:
            logger.info("Stopping experiment")
            self.status = "stopping"
            
            # Simulate stopping operations
            await asyncio.sleep(1)
            
            self.status = "idle"
            self.current_operation = None
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop experiment: {str(e)}")
            return False
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current status of OT2 controller."""
        return {
            "status": self.status,
            "current_operation": self.current_operation,
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat()
        }
    
    async def cleanup(self) -> None:
        """Cleanup OT2 controller resources."""
        try:
            logger.info("Cleaning up OT2 controller")
            
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
                
            self.status = "cleaned"
            
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise 
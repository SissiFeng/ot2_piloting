import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import numpy as np
import json
import paho.mqtt.client as mqtt
import asyncio

from ..interfaces.data_collector import IDataCollector
from ..config.ot2_config import OT2Config

logger = logging.getLogger(__name__)

class ColorSensorCollector(IDataCollector):
    """Simulated color sensor data collector."""
    
    def __init__(self):
        self.mqtt_client = None
        self.config = None
        self.latest_data = {}
        self.data_history = []
        
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize color sensor collector."""
        try:
            logger.info("Initializing color sensor collector")
            self.config = OT2Config(**config)
            
            # Setup MQTT client for sensor data
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
            
            # Setup message handling
            self.mqtt_client.on_message = self._on_message
            self.mqtt_client.subscribe("color-mixing/picow/+/as7341")
            
            self.mqtt_client.loop_start()
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize color sensor: {str(e)}")
            return False
    
    def _on_message(self, client, userdata, msg):
        """Handle incoming sensor data."""
        try:
            payload = json.loads(msg.payload.decode())
            self.latest_data = payload
            self.data_history.append(payload)
        except Exception as e:
            logger.error(f"Error processing sensor data: {str(e)}")
    
    async def collect_data(self, experiment_id: str) -> Dict[str, Any]:
        """Collect color sensor data."""
        try:
            logger.info(f"Collecting data for experiment {experiment_id}")
            
            # Simulate sensor reading delay
            await asyncio.sleep(0.5)
            
            # Generate simulated spectral data
            wavelengths = np.linspace(350, 850, 500)
            intensities = self._simulate_spectrum()
            
            data = {
                "experiment_id": experiment_id,
                "timestamp": datetime.now().isoformat(),
                "wavelengths": wavelengths.tolist(),
                "intensities": intensities.tolist(),
                "metadata": {
                    "integration_time_ms": self.config.measurement_config["integration_time_ms"],
                    "sensor_temperature": 25.0,
                    "sensor_gain": 1.0
                }
            }
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to collect data: {str(e)}")
            raise
    
    def _simulate_spectrum(self) -> np.ndarray:
        """Generate simulated spectral data."""
        # Create base spectrum
        wavelengths = np.linspace(350, 850, 500)
        spectrum = np.zeros_like(wavelengths)
        
        # Add peaks for RGB colors
        spectrum += self._gaussian(wavelengths, 650, 30, 0.8)  # Red
        spectrum += self._gaussian(wavelengths, 550, 30, 0.6)  # Green
        spectrum += self._gaussian(wavelengths, 450, 30, 0.7)  # Blue
        
        # Add noise
        noise = np.random.normal(0, 0.02, wavelengths.shape)
        spectrum += noise
        
        return np.clip(spectrum, 0, 1)
    
    def _gaussian(self, x: np.ndarray, mu: float, sigma: float, amplitude: float) -> np.ndarray:
        """Generate Gaussian peak."""
        return amplitude * np.exp(-(x - mu)**2 / (2 * sigma**2))
    
    async def validate_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate collected data."""
        validation_results = {
            "is_valid": True,
            "checks": []
        }
        
        # Check required fields
        required_fields = ["wavelengths", "intensities", "timestamp"]
        for field in required_fields:
            if field not in data:
                validation_results["is_valid"] = False
                validation_results["checks"].append({
                    "check": "required_field",
                    "field": field,
                    "status": "failed"
                })
        
        # Check data dimensions
        if "wavelengths" in data and "intensities" in data:
            if len(data["wavelengths"]) != len(data["intensities"]):
                validation_results["is_valid"] = False
                validation_results["checks"].append({
                    "check": "data_dimensions",
                    "status": "failed",
                    "message": "Wavelengths and intensities must have same length"
                })
        
        return validation_results
    
    async def save_data(self, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> str:
        """Save collected data."""
        try:
            # Simulate data saving
            save_id = f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            saved_data = {
                "id": save_id,
                "data": data,
                "metadata": metadata or {},
                "saved_at": datetime.now().isoformat()
            }
            
            self.data_history.append(saved_data)
            logger.info(f"Saved data with ID: {save_id}")
            
            return save_id
            
        except Exception as e:
            logger.error(f"Failed to save data: {str(e)}")
            raise
    
    async def get_data_history(self, experiment_id: str,
                             start_time: Optional[datetime] = None,
                             end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get historical data."""
        try:
            filtered_history = []
            
            for entry in self.data_history:
                if entry.get("data", {}).get("experiment_id") == experiment_id:
                    entry_time = datetime.fromisoformat(entry["saved_at"])
                    
                    if start_time and entry_time < start_time:
                        continue
                    if end_time and entry_time > end_time:
                        continue
                        
                    filtered_history.append(entry)
            
            return filtered_history
            
        except Exception as e:
            logger.error(f"Failed to get data history: {str(e)}")
            raise 
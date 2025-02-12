from typing import Dict, Any, List
from pydantic import Field

from .base_config import BaseConfig, HardwareConfig

class OT2HardwareConfig(HardwareConfig):
    """OT-2 specific hardware configuration."""
    pipette_types: Dict[str, str]
    deck_layout: Dict[str, Any]
    labware_config: Dict[str, Any]
    max_volume_ul: float = 300.0
    min_volume_ul: float = 1.0
    
    # MQTT configuration
    mqtt_broker: str
    mqtt_port: int = 8883
    mqtt_username: str
    mqtt_password: str
    mqtt_topics: Dict[str, str]

class OT2Config(BaseConfig):
    """OT-2 specific configuration."""
    experiment_type: str = "color_mixing"
    
    # Override hardware with OT2-specific config
    hardware: OT2HardwareConfig
    
    # Color mixing specific configuration
    color_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "available_colors": ["red", "yellow", "blue"],
            "max_total_volume": 300.0,
            "min_color_volume": 1.0,
            "mixing_strategy": "sequential"
        }
    )
    
    # Spectral measurement configuration
    measurement_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "wavelength_range": [350, 850],
            "measurement_points": 500,
            "integration_time_ms": 100
        }
    )
    
    class Config:
        arbitrary_types_allowed = True 
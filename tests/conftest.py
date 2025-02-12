import pytest
from typing import Dict, Any
import asyncio
from datetime import datetime

from app.core.config.ot2_config import OT2Config, OT2HardwareConfig

@pytest.fixture
def mock_config() -> Dict[str, Any]:
    """Create mock configuration for testing."""
    return {
        "experiment_type": "color_mixing",
        "experiment_id": "test_exp_001",
        "description": "Test experiment",
        "hardware": {
            "device_id": "OT2CEP20240218",
            "device_type": "ot2",
            "connection_params": {},
            "pipette_types": {"left": "p300_single"},
            "deck_layout": {},
            "labware_config": {},
            "mqtt_broker": "test.mosquitto.org",
            "mqtt_port": 8883,
            "mqtt_username": "test",
            "mqtt_password": "test"
        },
        "color_config": {
            "available_colors": ["red", "yellow", "blue"],
            "max_total_volume": 300.0,
            "min_color_volume": 1.0,
            "mixing_strategy": "sequential"
        },
        "measurement_config": {
            "wavelength_range": [350, 850],
            "measurement_points": 500,
            "integration_time_ms": 100
        }
    }

@pytest.fixture
def ot2_config(mock_config) -> OT2Config:
    """Create OT2Config instance for testing."""
    return OT2Config(**mock_config)

@pytest.fixture
def mock_experiment_data() -> Dict[str, Any]:
    """Create mock experiment data for testing."""
    return {
        "parameters": {
            "volumes": {
                "red": 100.0,
                "yellow": 50.0,
                "blue": 25.0
            }
        },
        "results": {
            "wavelengths": list(range(350, 851)),
            "intensities": [0.5] * 501,
            "timestamp": datetime.now().isoformat()
        }
    }

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop()
    yield loop
    loop.close() 
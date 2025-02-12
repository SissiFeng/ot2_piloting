import pytest
from unittest.mock import MagicMock, patch
import numpy as np
from datetime import datetime, timedelta

from app.core.ot2.color_sensor import ColorSensorCollector

@pytest.mark.asyncio
async def test_initialize(mock_config):
    """Test sensor initialization."""
    with patch('paho.mqtt.client.Client') as mock_mqtt:
        collector = ColorSensorCollector()
        success = await collector.initialize(mock_config)
        
        assert success is True
        mock_mqtt.return_value.connect.assert_called_once()
        mock_mqtt.return_value.subscribe.assert_called_once_with("color-mixing/picow/+/as7341")

@pytest.mark.asyncio
async def test_collect_data(mock_config):
    """Test data collection."""
    with patch('paho.mqtt.client.Client'):
        collector = ColorSensorCollector()
        await collector.initialize(mock_config)
        
        data = await collector.collect_data("test_exp_001")
        
        assert "experiment_id" in data
        assert "wavelengths" in data
        assert "intensities" in data
        assert "metadata" in data
        assert len(data["wavelengths"]) == len(data["intensities"])
        assert data["metadata"]["integration_time_ms"] == mock_config["measurement_config"]["integration_time_ms"]

@pytest.mark.asyncio
async def test_validate_data(mock_config):
    """Test data validation."""
    with patch('paho.mqtt.client.Client'):
        collector = ColorSensorCollector()
        await collector.initialize(mock_config)
        
        # Test valid data
        valid_data = {
            "wavelengths": [1, 2, 3],
            "intensities": [0.1, 0.2, 0.3],
            "timestamp": datetime.now().isoformat()
        }
        validation_result = await collector.validate_data(valid_data)
        assert validation_result["is_valid"] is True
        
        # Test invalid data
        invalid_data = {
            "wavelengths": [1, 2, 3],
            "intensities": [0.1, 0.2],  # Different length
            "timestamp": datetime.now().isoformat()
        }
        validation_result = await collector.validate_data(invalid_data)
        assert validation_result["is_valid"] is False

@pytest.mark.asyncio
async def test_save_data(mock_config):
    """Test data saving."""
    with patch('paho.mqtt.client.Client'):
        collector = ColorSensorCollector()
        await collector.initialize(mock_config)
        
        test_data = {
            "wavelengths": [1, 2, 3],
            "intensities": [0.1, 0.2, 0.3],
            "timestamp": datetime.now().isoformat()
        }
        
        save_id = await collector.save_data(test_data, {"test_meta": "value"})
        
        assert save_id.startswith("data_")
        assert len(collector.data_history) == 1
        assert collector.data_history[0]["data"] == test_data
        assert collector.data_history[0]["metadata"] == {"test_meta": "value"}

@pytest.mark.asyncio
async def test_get_data_history(mock_config):
    """Test retrieving data history."""
    with patch('paho.mqtt.client.Client'):
        collector = ColorSensorCollector()
        await collector.initialize(mock_config)
        
        # Save some test data
        test_data = {
            "experiment_id": "test_exp_001",
            "wavelengths": [1, 2, 3],
            "intensities": [0.1, 0.2, 0.3],
            "timestamp": datetime.now().isoformat()
        }
        
        await collector.save_data(test_data)
        await collector.save_data(test_data)  # Save twice
        
        # Test without time filters
        history = await collector.get_data_history("test_exp_001")
        assert len(history) == 2
        
        # Test with time filters
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now() + timedelta(hours=1)
        history = await collector.get_data_history(
            "test_exp_001",
            start_time=start_time,
            end_time=end_time
        )
        assert len(history) == 2

@pytest.mark.asyncio
async def test_simulate_spectrum(mock_config):
    """Test spectrum simulation."""
    with patch('paho.mqtt.client.Client'):
        collector = ColorSensorCollector()
        await collector.initialize(mock_config)
        
        spectrum = collector._simulate_spectrum()
        
        assert isinstance(spectrum, np.ndarray)
        assert len(spectrum) == 500
        assert np.all(spectrum >= 0)
        assert np.all(spectrum <= 1)

@pytest.mark.asyncio
async def test_mqtt_message_handling(mock_config):
    """Test MQTT message handling."""
    with patch('paho.mqtt.client.Client'):
        collector = ColorSensorCollector()
        await collector.initialize(mock_config)
        
        # Simulate receiving MQTT message
        test_payload = {
            "sensor_data": {"value": 123},
            "timestamp": datetime.now().isoformat()
        }
        
        # Create mock message
        mock_msg = MagicMock()
        mock_msg.payload = bytes(str(test_payload), 'utf-8')
        
        # Test message handler
        collector._on_message(None, None, mock_msg)
        
        assert len(collector.data_history) > 0 
import pytest
from unittest.mock import MagicMock, patch
import asyncio
from datetime import datetime

from app.core.ot2.ot2_controller import OT2Controller

@pytest.mark.asyncio
async def test_initialize(mock_config):
    """Test controller initialization."""
    with patch('paho.mqtt.client.Client') as mock_mqtt:
        controller = OT2Controller()
        success = await controller.initialize(mock_config)
        
        assert success is True
        assert controller.status == "initialized"
        assert controller.session_id is not None
        mock_mqtt.return_value.connect.assert_called_once()

@pytest.mark.asyncio
async def test_run_experiment(mock_config, mock_experiment_data):
    """Test running an experiment."""
    with patch('paho.mqtt.client.Client'):
        controller = OT2Controller()
        await controller.initialize(mock_config)
        
        result = await controller.run_experiment(mock_experiment_data["parameters"])
        
        assert result["status"] == "success"
        assert result["session_id"] == controller.session_id
        assert "timestamp" in result
        assert result["operations_completed"] is True
        assert controller.status == "idle"

@pytest.mark.asyncio
async def test_stop_experiment(mock_config):
    """Test stopping an experiment."""
    with patch('paho.mqtt.client.Client'):
        controller = OT2Controller()
        await controller.initialize(mock_config)
        
        success = await controller.stop_experiment()
        
        assert success is True
        assert controller.status == "idle"
        assert controller.current_operation is None

@pytest.mark.asyncio
async def test_get_status(mock_config):
    """Test getting controller status."""
    with patch('paho.mqtt.client.Client'):
        controller = OT2Controller()
        await controller.initialize(mock_config)
        
        status = await controller.get_status()
        
        assert "status" in status
        assert "session_id" in status
        assert "timestamp" in status
        assert status["current_operation"] is None

@pytest.mark.asyncio
async def test_cleanup(mock_config):
    """Test controller cleanup."""
    with patch('paho.mqtt.client.Client') as mock_mqtt:
        controller = OT2Controller()
        await controller.initialize(mock_config)
        
        await controller.cleanup()
        
        assert controller.status == "cleaned"
        mock_mqtt.return_value.loop_stop.assert_called_once()
        mock_mqtt.return_value.disconnect.assert_called_once()

@pytest.mark.asyncio
async def test_error_handling(mock_config):
    """Test error handling during experiment."""
    with patch('paho.mqtt.client.Client'):
        controller = OT2Controller()
        await controller.initialize(mock_config)
        
        # Test with invalid parameters
        with pytest.raises(Exception):
            await controller.run_experiment({"invalid": "params"})
        
        assert controller.status == "error"

@pytest.mark.asyncio
async def test_concurrent_operations(mock_config, mock_experiment_data):
    """Test handling concurrent operations."""
    with patch('paho.mqtt.client.Client'):
        controller = OT2Controller()
        await controller.initialize(mock_config)
        
        # Start multiple operations concurrently
        tasks = [
            controller.run_experiment(mock_experiment_data["parameters"])
            for _ in range(3)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all operations completed successfully
        assert all(r["status"] == "success" for r in results)
        assert controller.status == "idle" 
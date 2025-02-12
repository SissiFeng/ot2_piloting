from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class HardwareConfig(BaseModel):
    """Hardware configuration base model."""
    device_id: str
    device_type: str
    connection_params: Dict[str, Any]
    calibration_data: Optional[Dict[str, Any]] = None

class OptimizationConfig(BaseModel):
    """Optimization configuration base model."""
    method: str = "bayesian"
    max_iterations: int = 100
    convergence_tolerance: float = 0.01
    acquisition_function: str = "ei"
    exploration_weight: float = 0.1
    constraints: Dict[str, Any] = Field(default_factory=dict)

class MonitoringConfig(BaseModel):
    """Monitoring configuration base model."""
    metrics: Dict[str, Any] = Field(default_factory=dict)
    logging_level: str = "INFO"
    alert_thresholds: Dict[str, float] = Field(default_factory=dict)

class BaseConfig(BaseModel):
    """Base configuration for experiments."""
    experiment_type: str
    experiment_id: Optional[str] = None
    description: Optional[str] = None
    
    # Hardware configuration
    hardware: HardwareConfig
    
    # Optimization configuration
    optimization: OptimizationConfig = Field(default_factory=OptimizationConfig)
    
    # Monitoring configuration
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    
    # Database configuration
    database_config: Dict[str, Any] = Field(default_factory=dict)
    
    # Additional custom configuration
    custom_config: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True 
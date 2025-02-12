from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class IExperimentController(ABC):
    """Interface for experiment controller implementations."""
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the experiment controller with given configuration.
        
        Args:
            config: Configuration dictionary for initialization
            
        Returns:
            bool: True if initialization successful
        """
        pass
    
    @abstractmethod
    async def run_experiment(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run experiment with given parameters.
        
        Args:
            params: Experiment parameters
            
        Returns:
            Dict containing experiment results
        """
        pass
    
    @abstractmethod
    async def stop_experiment(self) -> bool:
        """Stop the current experiment.
        
        Returns:
            bool: True if stop successful
        """
        pass
    
    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """Get current status of the experiment controller.
        
        Returns:
            Dict containing status information
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup resources used by the controller."""
        pass 
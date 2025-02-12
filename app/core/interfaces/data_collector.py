from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

class IDataCollector(ABC):
    """Interface for data collection implementations."""
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the data collector with given configuration.
        
        Args:
            config: Configuration dictionary for initialization
            
        Returns:
            bool: True if initialization successful
        """
        pass
    
    @abstractmethod
    async def collect_data(self, experiment_id: str) -> Dict[str, Any]:
        """Collect data for the given experiment.
        
        Args:
            experiment_id: Identifier for the experiment
            
        Returns:
            Dict containing collected data
        """
        pass
    
    @abstractmethod
    async def validate_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate collected data.
        
        Args:
            data: Data to validate
            
        Returns:
            Dict containing validation results
        """
        pass
    
    @abstractmethod
    async def save_data(self, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> str:
        """Save collected data with optional metadata.
        
        Args:
            data: Data to save
            metadata: Optional metadata to save with data
            
        Returns:
            str: Identifier for saved data
        """
        pass
    
    @abstractmethod
    async def get_data_history(self, experiment_id: str, start_time: Optional[datetime] = None,
                             end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get historical data for the experiment.
        
        Args:
            experiment_id: Identifier for the experiment
            start_time: Optional start time for history
            end_time: Optional end time for history
            
        Returns:
            List of historical data entries
        """
        pass 
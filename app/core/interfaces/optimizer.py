from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from uuid import UUID

class IOptimizer(ABC):
    """Interface for optimization implementations."""
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the optimizer with given configuration.
        
        Args:
            config: Configuration dictionary for initialization
            
        Returns:
            bool: True if initialization successful
        """
        pass
    
    @abstractmethod
    async def optimize(self, target: Dict[str, Any], constraints: Dict[str, Any],
                      current_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Perform optimization step.
        
        Args:
            target: Target objectives
            constraints: Optimization constraints
            current_data: Optional current experiment data
            
        Returns:
            Dict containing next suggested parameters
        """
        pass
    
    @abstractmethod
    async def update_model(self, experiment_data: Dict[str, Any]) -> None:
        """Update optimization model with new experimental data.
        
        Args:
            experiment_data: New experimental data
        """
        pass
    
    @abstractmethod
    async def get_optimization_status(self) -> Dict[str, Any]:
        """Get current status of optimization.
        
        Returns:
            Dict containing optimization status
        """
        pass
    
    @abstractmethod
    async def check_convergence(self, tolerance: float = 0.01) -> bool:
        """Check if optimization has converged.
        
        Args:
            tolerance: Convergence tolerance
            
        Returns:
            bool: True if converged
        """
        pass 
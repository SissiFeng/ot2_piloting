from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import logging
import asyncio
from datetime import datetime

from ..interfaces.experiment_controller import IExperimentController
from ..interfaces.data_collector import IDataCollector
from ..interfaces.optimizer import IOptimizer
from ..config.base_config import BaseConfig

logger = logging.getLogger(__name__)

class BaseWorkflow(ABC):
    """Base class for experiment workflows."""
    
    def __init__(self, 
                 controller: IExperimentController,
                 collector: IDataCollector,
                 optimizer: IOptimizer,
                 config: BaseConfig):
        """Initialize workflow with required components.
        
        Args:
            controller: Experiment controller implementation
            collector: Data collector implementation
            optimizer: Optimizer implementation
            config: Experiment configuration
        """
        self.controller = controller
        self.collector = collector
        self.optimizer = optimizer
        self.config = config
        self.status = "initialized"
        self.start_time = None
        self.end_time = None
        
    @abstractmethod
    async def setup(self) -> bool:
        """Setup workflow before execution.
        
        Returns:
            bool: True if setup successful
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup after workflow execution."""
        pass
    
    @abstractmethod
    async def handle_error(self, error: Exception) -> None:
        """Handle workflow errors.
        
        Args:
            error: Exception that occurred
        """
        pass
    
    async def execute(self) -> Dict[str, Any]:
        """Execute the workflow.
        
        Returns:
            Dict containing workflow results
        """
        try:
            logger.info("Starting workflow execution")
            self.start_time = datetime.now()
            self.status = "running"
            
            # Setup components
            if not await self.setup():
                raise Exception("Workflow setup failed")
            
            # Initialize components
            await self.controller.initialize(self.config.dict())
            await self.collector.initialize(self.config.dict())
            await self.optimizer.initialize(self.config.dict())
            
            results = await self._run_workflow_loop()
            
            self.status = "completed"
            return results
            
        except Exception as e:
            self.status = "failed"
            logger.error(f"Workflow execution failed: {str(e)}")
            await self.handle_error(e)
            raise
            
        finally:
            self.end_time = datetime.now()
            await self.cleanup()
    
    async def _run_workflow_loop(self) -> Dict[str, Any]:
        """Run the main workflow loop.
        
        Returns:
            Dict containing workflow results
        """
        iteration = 0
        results = {}
        
        while iteration < self.config.optimization.max_iterations:
            # Collect current data
            current_data = await self.collector.collect_data(self.config.experiment_id)
            
            # Check if optimization has converged
            if await self.optimizer.check_convergence(self.config.optimization.convergence_tolerance):
                logger.info("Optimization converged")
                break
                
            # Get next parameters
            next_params = await self.optimizer.optimize(
                target=self.config.optimization.constraints,
                constraints=self.config.optimization.constraints,
                current_data=current_data
            )
            
            # Run experiment
            experiment_results = await self.controller.run_experiment(next_params)
            
            # Update optimizer
            await self.optimizer.update_model(experiment_results)
            
            # Save results
            results[iteration] = {
                "parameters": next_params,
                "results": experiment_results,
                "optimization_status": await self.optimizer.get_optimization_status()
            }
            
            iteration += 1
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """Get current workflow status.
        
        Returns:
            Dict containing status information
        """
        return {
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "controller_status": self.controller.get_status(),
            "optimization_status": self.optimizer.get_optimization_status()
        } 
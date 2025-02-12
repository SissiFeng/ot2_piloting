"""Machine learning and Bayesian optimization integration for experiment optimization."""
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import logging
from datetime import datetime
from uuid import UUID

from ..optimization.bayesian_optimizer import ColorMixingOptimizer
from ..etl.transformations import SpectralDataTransformer
from ..storage.models import (
    MLAnalysis, MLFeatureSet, MLModelInput, MLModelOutput,
    OptimizationResult, ReviewStatus
)

logger = logging.getLogger(__name__)

class ExperimentOptimizer:
    """Experiment optimizer using Bayesian Optimization and ML."""
    
    def __init__(self, db_manager=None):
        """Initialize optimizer with database manager."""
        self.db_manager = db_manager
        self.bo_optimizer = None
        self.data_transformer = SpectralDataTransformer()
        
    async def initialize_optimization(self, 
                                   experiment_id: UUID,
                                   target_spectrum: Optional[np.ndarray] = None,
                                   optimization_params: Optional[Dict[str, Any]] = None) -> MLAnalysis:
        """Initialize a new optimization run.
        
        Args:
            experiment_id: ID of the experiment (optional, will create new if None)
            target_spectrum: Target spectrum to match (optional)
            optimization_params: Additional optimization parameters
            
        Returns:
            MLAnalysis object for tracking optimization
        """
        try:
            # Set default optimization parameters
            params = {
                "max_iterations": 20,
                "convergence_threshold": 0.01,
                "total_volume": 300,
                "min_volume": 0,
                "max_volume": 100
            }
            if optimization_params:
                params.update(optimization_params)
            
            # Initialize Bayesian Optimizer
            bounds = {
                "red": [params["min_volume"], params["max_volume"]],
                "yellow": [params["min_volume"], params["max_volume"]],
                "blue": [params["min_volume"], params["max_volume"]]
            }
            
            self.bo_optimizer = ColorMixingOptimizer(
                bounds=bounds,
                n_initial_points=3,
                acquisition_function="ei"
            )
            
            # Create MLAnalysis record
            analysis = MLAnalysis(
                experiment_id=experiment_id,
                model_version="0.1.0",
                input_data={
                    "target_spectrum": target_spectrum.tolist() if target_spectrum is not None else None,
                    "optimization_params": params
                },
                output_data={
                    "current_iteration": 0,
                    "best_params": None,
                    "convergence_status": "running"
                }
            )
            
            if self.db_manager:
                analysis_id = await self.db_manager.create_ml_analysis(analysis)
                analysis.id = analysis_id
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to initialize optimization: {str(e)}")
            raise
            
    async def optimize_experiment(self, 
                                analysis: MLAnalysis,
                                max_iterations: int = 20,
                                convergence_threshold: float = 0.01) -> MLAnalysis:
        """Run optimization process.
        
        Args:
            analysis: MLAnalysis object
            max_iterations: Maximum number of iterations
            convergence_threshold: Convergence threshold
            
        Returns:
            Updated MLAnalysis object
        """
        try:
            current_iteration = 0
            best_score = float('inf')
            
            while current_iteration < max_iterations:
                # Get next parameters
                next_params = self.bo_optimizer.suggest_next_experiment()
                
                # Run experiment
                result = await self._run_experiment(next_params)
                
                # Update model
                await self.update_model(result)
                
                # Check convergence
                convergence_status = self.bo_optimizer.compute_convergence_criteria()
                if convergence_status["converged"]:
                    break
                    
                current_iteration += 1
                
            # Update analysis record
            analysis.output_data.update({
                "current_iteration": current_iteration,
                "best_params": self.bo_optimizer.best_params,
                "convergence_status": "converged" if convergence_status["converged"] else "max_iterations"
            })
            
            if self.db_manager:
                await self.db_manager.update_ml_analysis_review(
                    analysis.id,
                    ReviewStatus.COMPLETED,
                    None  # No reviewer for automated process
                )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Optimization failed: {str(e)}")
            raise
            
    async def update_model(self, experiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update optimization model with new experimental data.
        
        Args:
            experiment_data: New experimental data
            
        Returns:
            Dictionary containing updated status
        """
        try:
            # Extract relevant data
            parameters = np.array([
                experiment_data["parameters"]["volumes"]["red"],
                experiment_data["parameters"]["volumes"]["yellow"],
                experiment_data["parameters"]["volumes"]["blue"]
            ]).reshape(1, -1)
            
            # Calculate objective value
            spectrum = experiment_data["results"]["spectrum"]
            target_spectrum = self.bo_optimizer.target_spectrum
            
            if target_spectrum is not None:
                objective_value = self.data_transformer.calculate_metrics(
                    target_spectrum,
                    spectrum
                )["rmse"]
            else:
                # Use default objective if no target spectrum
                objective_value = -np.max(spectrum)  # Maximize peak intensity
            
            # Update optimizer
            self.bo_optimizer.update_model(parameters, np.array([objective_value]))
            
            # Get optimization status
            status = self.bo_optimizer.get_optimization_state()
            
            # Create convergence plot data
            plot_data = {
                "iterations": list(range(len(self.bo_optimizer.y))),
                "objective_values": self.bo_optimizer.y.tolist(),
                "best_value": float(self.bo_optimizer.best_value)
            }
            
            return {
                "current_iteration": len(self.bo_optimizer.y),
                "best_params": status["best_params"],
                "suggested_params": self.bo_optimizer.suggest_next_experiment(),
                "convergence_plot": plot_data
            }
            
        except Exception as e:
            logger.error(f"Failed to update model: {str(e)}")
            raise
            
    async def get_optimization_status(self, analysis_id: UUID) -> Dict[str, Any]:
        """Get current optimization status.
        
        Args:
            analysis_id: ID of the MLAnalysis record
            
        Returns:
            Dictionary containing optimization status
        """
        try:
            if not self.bo_optimizer:
                raise ValueError("Optimizer not initialized")
                
            status = self.bo_optimizer.get_optimization_state()
            
            return {
                "current_iteration": status["n_observations"],
                "best_params": status["best_params"],
                "suggested_params": self.bo_optimizer.suggest_next_experiment(),
                "convergence_plot": {
                    "iterations": list(range(status["n_observations"])),
                    "objective_values": self.bo_optimizer.y.tolist() if self.bo_optimizer.y is not None else [],
                    "best_value": float(self.bo_optimizer.best_value)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get optimization status: {str(e)}")
            raise
        
    async def _run_experiment(self, parameters: Dict[str, float]) -> np.ndarray:
        """Run or simulate experiment with given parameters.
        
        This is a placeholder - replace with actual experiment execution
        or more sophisticated simulation.
        """
        # Simple simulation - replace with actual experiment
        spectrum = self.data_transformer._predict_spectrum(parameters)
        return spectrum
        
    async def export_optimization_results(self, analysis_id: UUID) -> Dict[str, Any]:
        """Export optimization results for analysis."""
        if not self.db_manager:
            raise ValueError("Database manager not initialized")
            
        analysis = await self.db_manager.get_ml_analysis(analysis_id)
        if not analysis:
            raise ValueError(f"Analysis {analysis_id} not found")
            
        # Extract history
        history = [{
            'iteration': r.iteration,
            'parameters': r.parameters,
            'objective': r.objective_value,
            'metrics': r.metrics,
            'predicted_mean': r.predicted_mean,
            'predicted_std': r.predicted_std,
            'timestamp': r.created_at.isoformat()
        } for r in analysis.optimization_history]
        
        return {
            'experiment_id': str(analysis.experiment_id),
            'model_version': analysis.model_version,
            'target_spectrum': analysis.target_spectrum,
            'constraints': analysis.optimization_constraints,
            'best_parameters': analysis.best_parameters,
            'final_metrics': analysis.optimization_metrics,
            'convergence_status': analysis.convergence_status,
            'history': history
        }

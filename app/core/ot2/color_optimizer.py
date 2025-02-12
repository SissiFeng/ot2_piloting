import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from datetime import datetime
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel

from ..interfaces.optimizer import IOptimizer
from ..config.ot2_config import OT2Config

logger = logging.getLogger(__name__)

class ColorMixingOptimizer(IOptimizer):
    """Color mixing optimizer using Bayesian optimization."""
    
    def __init__(self):
        self.config = None
        self.gp = None
        self.X_train = []
        self.y_train = []
        self.best_params = None
        self.best_score = float('-inf')
        self.iteration = 0
        
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize optimizer with configuration."""
        try:
            logger.info("Initializing color mixing optimizer")
            self.config = OT2Config(**config)
            
            # Initialize Gaussian Process model
            kernel = ConstantKernel(1.0) * RBF([1.0, 1.0, 1.0])
            self.gp = GaussianProcessRegressor(
                kernel=kernel,
                n_restarts_optimizer=10,
                random_state=42
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize optimizer: {str(e)}")
            return False
    
    async def optimize(self, target: Dict[str, Any], constraints: Dict[str, Any],
                      current_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Perform optimization step."""
        try:
            logger.info("Running optimization step")
            
            if len(self.X_train) < 3:
                # Initial exploration phase
                params = self._generate_random_params(constraints)
            else:
                # Bayesian optimization phase
                params = self._bayesian_optimization_step(constraints)
            
            self.iteration += 1
            
            return {
                "volumes": {
                    "red": float(params[0]),
                    "yellow": float(params[1]),
                    "blue": float(params[2])
                },
                "iteration": self.iteration,
                "optimization_type": "random" if len(self.X_train) < 3 else "bayesian"
            }
            
        except Exception as e:
            logger.error(f"Optimization step failed: {str(e)}")
            raise
    
    async def update_model(self, experiment_data: Dict[str, Any]) -> None:
        """Update optimization model with new data."""
        try:
            # Extract parameters and results
            params = experiment_data["parameters"]["volumes"]
            X_new = np.array([params["red"], params["yellow"], params["blue"]]).reshape(1, -1)
            
            # Calculate score from spectral data
            score = self._calculate_score(experiment_data.get("results", {}))
            
            # Update training data
            self.X_train.append(X_new)
            self.y_train.append(score)
            
            # Update best result
            if score > self.best_score:
                self.best_score = score
                self.best_params = params
            
            # Retrain model if we have enough data
            if len(self.X_train) >= 3:
                X = np.vstack(self.X_train)
                y = np.array(self.y_train)
                self.gp.fit(X, y)
                
        except Exception as e:
            logger.error(f"Model update failed: {str(e)}")
            raise
    
    async def get_optimization_status(self) -> Dict[str, Any]:
        """Get current optimization status."""
        return {
            "iteration": self.iteration,
            "best_score": float(self.best_score) if self.best_score is not None else None,
            "best_params": self.best_params,
            "n_observations": len(self.X_train),
            "model_trained": self.gp is not None and len(self.X_train) >= 3,
            "timestamp": datetime.now().isoformat()
        }
    
    async def check_convergence(self, tolerance: float = 0.01) -> bool:
        """Check if optimization has converged."""
        if len(self.y_train) < 5:
            return False
            
        # Check if recent improvements are below tolerance
        recent_scores = self.y_train[-5:]
        improvements = np.diff(recent_scores)
        return np.all(np.abs(improvements) < tolerance)
    
    def _generate_random_params(self, constraints: Dict[str, Any]) -> np.ndarray:
        """Generate random parameters within constraints."""
        max_volume = constraints.get("max_total_volume", 300.0)
        min_volume = constraints.get("min_volume", 0.0)
        
        while True:
            # Generate random volumes
            volumes = np.random.uniform(min_volume, max_volume/2, 3)
            
            # Check if total volume is within constraints
            if np.sum(volumes) <= max_volume:
                return volumes
    
    def _bayesian_optimization_step(self, constraints: Dict[str, Any]) -> np.ndarray:
        """Perform Bayesian optimization step."""
        max_volume = constraints.get("max_total_volume", 300.0)
        min_volume = constraints.get("min_volume", 0.0)
        
        def objective(x):
            # Predict mean and std from GP model
            mean, std = self.gp.predict(x.reshape(1, -1), return_std=True)
            # Upper confidence bound acquisition function
            return mean + 2.0 * std
        
        # Generate candidate points
        n_candidates = 1000
        candidates = []
        for _ in range(n_candidates):
            candidate = self._generate_random_params(constraints)
            candidates.append(candidate)
        
        candidates = np.vstack(candidates)
        
        # Evaluate acquisition function
        values = [objective(x) for x in candidates]
        
        # Select best candidate
        best_idx = np.argmax(values)
        return candidates[best_idx]
    
    def _calculate_score(self, results: Dict[str, Any]) -> float:
        """Calculate optimization score from results."""
        try:
            # Extract spectral data
            wavelengths = np.array(results.get("wavelengths", []))
            intensities = np.array(results.get("intensities", []))
            
            if len(wavelengths) == 0 or len(intensities) == 0:
                return 0.0
            
            # Calculate simple score based on peak characteristics
            peak_intensity = np.max(intensities)
            peak_width = self._calculate_peak_width(intensities)
            
            # Combine metrics into single score
            score = peak_intensity * (1.0 / (1.0 + peak_width))
            
            return float(score)
            
        except Exception as e:
            logger.error(f"Score calculation failed: {str(e)}")
            return 0.0
    
    def _calculate_peak_width(self, intensities: np.ndarray) -> float:
        """Calculate width of spectral peak."""
        try:
            # Find points above half maximum
            max_intensity = np.max(intensities)
            half_max = max_intensity / 2
            above_half = intensities >= half_max
            
            # Calculate width
            indices = np.where(above_half)[0]
            if len(indices) > 0:
                return float(indices[-1] - indices[0])
            return 0.0
            
        except Exception as e:
            logger.error(f"Peak width calculation failed: {str(e)}")
            return 0.0 
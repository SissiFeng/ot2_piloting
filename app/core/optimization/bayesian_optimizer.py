"""Bayesian optimization for color mixing experiments."""
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel, Matern
from scipy.optimize import minimize
from scipy.stats import norm
import logging

logger = logging.getLogger(__name__)

class ColorMixingOptimizer:
    """Bayesian optimization for color mixing experiments."""
    
    def __init__(self, 
                 bounds: Dict[str, List[float]],
                 n_initial_points: int = 5,
                 random_state: int = 42,
                 acquisition_function: str = 'ei',
                 exploitation_weight: float = 0.1):
        """Initialize the optimizer.
        
        Args:
            bounds: Dictionary of parameter bounds
            n_initial_points: Number of initial random points
            random_state: Random seed
            acquisition_function: Type of acquisition function ('ei', 'ucb', 'pi')
            exploitation_weight: Weight for exploration-exploitation trade-off
        """
        self.bounds = bounds
        self.n_initial_points = n_initial_points
        self.random_state = random_state
        self.acquisition_function = acquisition_function
        self.exploitation_weight = exploitation_weight
        self.rng = np.random.RandomState(random_state)
        
        # Initialize Gaussian Process
        kernel = ConstantKernel(1.0) * Matern(length_scale=np.ones(len(bounds)),
                                             nu=2.5)
        self.gp = GaussianProcessRegressor(
            kernel=kernel,
            n_restarts_optimizer=10,
            random_state=random_state
        )
        
        self.X = None  # Observed parameters
        self.y = None  # Observed values
        self.best_value = float('inf')
        self.best_params = None
        
    def suggest_next_experiment(self, 
                              X: Optional[np.ndarray] = None, 
                              y: Optional[np.ndarray] = None) -> Dict[str, float]:
        """Suggest next experiment parameters using BO.
        
        Args:
            X: Observed parameters (optional)
            y: Observed values (optional)
            
        Returns:
            Dictionary of suggested parameters
        """
        if X is not None and y is not None:
            self.update_model(X, y)
            
        if self.X is None or len(self.X) < self.n_initial_points:
            # Generate random point for initial exploration
            return self._generate_random_point()
            
        # Optimize acquisition function
        bounds_list = [self.bounds[param] for param in sorted(self.bounds.keys())]
        x_next = self._optimize_acquisition(bounds_list)
        
        # Convert to dictionary
        return {param: x_next[i] for i, param in enumerate(sorted(self.bounds.keys()))}
        
    def update_model(self, 
                    new_X: np.ndarray, 
                    new_y: np.ndarray) -> None:
        """Update the GP model with new experimental data.
        
        Args:
            new_X: New parameter values
            new_y: New observed values
        """
        if self.X is None:
            self.X = new_X
            self.y = new_y
        else:
            self.X = np.vstack((self.X, new_X))
            self.y = np.concatenate((self.y, new_y))
            
        # Update best observation
        best_idx = np.argmin(self.y)
        if self.y[best_idx] < self.best_value:
            self.best_value = self.y[best_idx]
            self.best_params = self.X[best_idx]
            
        # Fit GP model
        try:
            self.gp.fit(self.X, self.y)
        except Exception as e:
            logger.error(f"Error fitting GP model: {str(e)}")
            raise
            
    def _generate_random_point(self) -> Dict[str, float]:
        """Generate random point within bounds."""
        point = {}
        for param, bound in self.bounds.items():
            point[param] = self.rng.uniform(bound[0], bound[1])
        return point
        
    def _optimize_acquisition(self, bounds_list: List[List[float]]) -> np.ndarray:
        """Optimize acquisition function."""
        best_x = None
        best_acquisition_value = float('inf')
        
        # Try multiple starting points
        n_starts = 5
        for _ in range(n_starts):
            x0 = [self.rng.uniform(b[0], b[1]) for b in bounds_list]
            res = minimize(
                lambda x: -self._acquisition(x.reshape(1, -1)),
                x0,
                bounds=bounds_list,
                method='L-BFGS-B'
            )
            
            if -res.fun < best_acquisition_value:
                best_acquisition_value = -res.fun
                best_x = res.x
                
        return best_x
        
    def _acquisition(self, X: np.ndarray) -> np.ndarray:
        """Calculate acquisition function value."""
        with np.errstate(divide='warn'):
            mu, sigma = self.gp.predict(X, return_std=True)
            
        if self.acquisition_function == 'ei':
            # Expected Improvement
            imp = self.best_value - mu
            Z = imp / sigma
            ei = imp * norm.cdf(Z) + sigma * norm.pdf(Z)
            return ei
            
        elif self.acquisition_function == 'ucb':
            # Upper Confidence Bound
            return mu - self.exploitation_weight * sigma
            
        elif self.acquisition_function == 'pi':
            # Probability of Improvement
            Z = (self.best_value - mu) / sigma
            return norm.cdf(Z)
            
        else:
            raise ValueError(f"Unknown acquisition function: {self.acquisition_function}")
            
    def get_optimization_state(self) -> Dict[str, Any]:
        """Get current state of optimization.
        
        Returns:
            Dictionary containing optimization state
        """
        return {
            'n_observations': len(self.X) if self.X is not None else 0,
            'best_value': self.best_value,
            'best_params': {param: self.best_params[i] 
                          for i, param in enumerate(sorted(self.bounds.keys()))}
                          if self.best_params is not None else None,
            'model_kernel_params': self.gp.kernel_.get_params() if self.X is not None else None,
            'acquisition_function': self.acquisition_function
        }
        
    def predict(self, X: np.ndarray, return_std: bool = False) -> np.ndarray:
        """Make predictions using the GP model.
        
        Args:
            X: Input parameters
            return_std: Whether to return standard deviation
            
        Returns:
            Predicted values (and optionally standard deviations)
        """
        if self.X is None:
            raise ValueError("Model has not been fitted yet")
        return self.gp.predict(X, return_std=return_std)
        
    def compute_convergence_criteria(self) -> Dict[str, float]:
        """Compute convergence criteria for the optimization.
        
        Returns:
            Dictionary of convergence metrics
        """
        if self.X is None or len(self.X) < 2:
            return {'converged': False}
            
        # Calculate improvement in last n iterations
        n_recent = min(5, len(self.X))
        recent_best = np.minimum.accumulate(self.y[-n_recent:])
        improvement_rate = (recent_best[0] - recent_best[-1]) / recent_best[0]
        
        # Calculate parameter stability
        recent_params = self.X[-n_recent:]
        param_stability = np.mean(np.std(recent_params, axis=0))
        
        # Calculate prediction uncertainty
        _, std = self.gp.predict(self.X[-n_recent:], return_std=True)
        uncertainty = np.mean(std)
        
        return {
            'improvement_rate': improvement_rate,
            'param_stability': param_stability,
            'uncertainty': uncertainty,
            'converged': improvement_rate < 0.01 and param_stability < 0.1
        } 
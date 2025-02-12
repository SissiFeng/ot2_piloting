"""Data transformation module for experiment optimization."""
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from scipy.interpolate import interp1d
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
from scipy.spatial.distance import directed_hausdorff
import logging

logger = logging.getLogger(__name__)

class SpectralDataTransformer:
    """Transform spectral data for optimization."""
    
    def __init__(self, wavelength_range: Tuple[float, float] = (350, 850),
                 n_points: int = 500):
        """Initialize transformer with wavelength range and resolution."""
        self.scaler = StandardScaler()
        self.wavelength_range = wavelength_range
        self.n_points = n_points
        self.uniform_wavelengths = np.linspace(wavelength_range[0], 
                                             wavelength_range[1], 
                                             n_points)
        
    def preprocess_spectrum(self, 
                          wavelengths: np.ndarray, 
                          intensities: np.ndarray,
                          remove_background: bool = True,
                          normalize: bool = True) -> np.ndarray:
        """Preprocess spectral data.
        
        Args:
            wavelengths: Wavelength values
            intensities: Intensity values
            remove_background: Whether to remove background noise
            normalize: Whether to normalize the spectrum
            
        Returns:
            Preprocessed spectrum array
        """
        try:
            # Remove background if needed
            if remove_background:
                background = np.percentile(intensities, 5)
                intensities = intensities - background
                intensities = np.clip(intensities, 0, None)
            
            # Interpolate to uniform wavelength grid
            interpolator = interp1d(wavelengths, 
                                  intensities, 
                                  kind='cubic',
                                  bounds_error=False,
                                  fill_value=0.0)
            uniform_intensities = interpolator(self.uniform_wavelengths)
            
            # Normalize if needed
            if normalize:
                if np.max(uniform_intensities) > 0:
                    uniform_intensities = uniform_intensities / np.max(uniform_intensities)
            
            return uniform_intensities
            
        except Exception as e:
            logger.error(f"Error in spectrum preprocessing: {str(e)}")
            raise
            
    def calculate_metrics(self, 
                         target_spectrum: np.ndarray, 
                         measured_spectrum: np.ndarray,
                         wavelengths: Optional[np.ndarray] = None) -> Dict[str, float]:
        """Calculate comparison metrics between target and measured spectra.
        
        Args:
            target_spectrum: Target spectrum intensities
            measured_spectrum: Measured spectrum intensities
            wavelengths: Optional wavelength values for distance calculations
            
        Returns:
            Dictionary of metric values
        """
        if wavelengths is None:
            wavelengths = self.uniform_wavelengths
            
        try:
            # Basic metrics
            metrics = {
                'mae': mean_absolute_error(target_spectrum, measured_spectrum),
                'rmse': np.sqrt(mean_squared_error(target_spectrum, measured_spectrum)),
                'peak_error': np.abs(np.max(target_spectrum) - np.max(measured_spectrum)),
                'area_difference': np.abs(np.trapz(target_spectrum) - np.trapz(measured_spectrum))
            }
            
            # Hausdorff distance for shape comparison
            coords_target = np.column_stack((wavelengths, target_spectrum))
            coords_measured = np.column_stack((wavelengths, measured_spectrum))
            hausdorff_dist = directed_hausdorff(coords_target, coords_measured)[0]
            metrics['hausdorff'] = hausdorff_dist
            
            # Correlation coefficient
            metrics['correlation'] = np.corrcoef(target_spectrum, measured_spectrum)[0, 1]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error in metric calculation: {str(e)}")
            raise
            
    def create_optimization_target(self, 
                                 target_spectrum: np.ndarray,
                                 constraints: Dict[str, Any],
                                 metric_weights: Optional[Dict[str, float]] = None) -> callable:
        """Create optimization objective function.
        
        Args:
            target_spectrum: Target spectrum to match
            constraints: Experimental constraints
            metric_weights: Weights for different metrics in objective function
            
        Returns:
            Objective function for optimization
        """
        if metric_weights is None:
            metric_weights = {
                'mae': 0.4,
                'rmse': 0.3,
                'hausdorff': 0.2,
                'correlation': 0.1
            }
            
        def objective(parameters: Dict[str, float]) -> float:
            """Calculate objective value for given parameters."""
            try:
                # Check constraints
                total_volume = sum(parameters.values())
                if total_volume > constraints.get('max_volume', float('inf')):
                    return float('inf')
                
                # Generate predicted spectrum (placeholder - replace with actual model)
                predicted_spectrum = self._predict_spectrum(parameters)
                
                # Calculate metrics
                metrics = self.calculate_metrics(target_spectrum, predicted_spectrum)
                
                # Combine metrics into single objective
                objective_value = sum(weight * metrics[metric] 
                                   for metric, weight in metric_weights.items())
                
                return objective_value
                
            except Exception as e:
                logger.error(f"Error in objective function: {str(e)}")
                raise
                
        return objective
        
    def _predict_spectrum(self, parameters: Dict[str, float]) -> np.ndarray:
        """Predict spectrum from mixing parameters.
        
        This is a placeholder - replace with actual spectral mixing model.
        """
        # Simple linear mixing model - replace with more sophisticated model
        spectrum = np.zeros_like(self.uniform_wavelengths)
        for component, amount in parameters.items():
            if component == 'R':
                peak_wavelength = 650  # Red
            elif component == 'G':
                peak_wavelength = 550  # Green
            elif component == 'B':
                peak_wavelength = 450  # Blue
            else:
                continue
                
            # Generate Gaussian peak
            spectrum += amount * np.exp(-(self.uniform_wavelengths - peak_wavelength)**2 / 1000)
            
        return spectrum
        
    def extract_features(self, spectrum: np.ndarray) -> Dict[str, float]:
        """Extract features from spectrum for machine learning.
        
        Args:
            spectrum: Input spectrum
            
        Returns:
            Dictionary of extracted features
        """
        features = {
            'max_intensity': np.max(spectrum),
            'total_intensity': np.sum(spectrum),
            'peak_wavelength': self.uniform_wavelengths[np.argmax(spectrum)],
            'width_50': self._calculate_width(spectrum, 0.5),
            'width_10': self._calculate_width(spectrum, 0.1),
            'skewness': self._calculate_skewness(spectrum),
            'kurtosis': self._calculate_kurtosis(spectrum)
        }
        return features
        
    def _calculate_width(self, spectrum: np.ndarray, height_fraction: float) -> float:
        """Calculate spectrum width at given height fraction."""
        threshold = np.max(spectrum) * height_fraction
        above_threshold = spectrum >= threshold
        indices = np.where(above_threshold)[0]
        if len(indices) >= 2:
            return self.uniform_wavelengths[indices[-1]] - self.uniform_wavelengths[indices[0]]
        return 0.0
        
    def _calculate_skewness(self, spectrum: np.ndarray) -> float:
        """Calculate spectrum skewness."""
        mean = np.average(self.uniform_wavelengths, weights=spectrum)
        variance = np.average((self.uniform_wavelengths - mean)**2, weights=spectrum)
        skewness = np.average((self.uniform_wavelengths - mean)**3, weights=spectrum)
        return skewness / variance**1.5 if variance > 0 else 0.0
        
    def _calculate_kurtosis(self, spectrum: np.ndarray) -> float:
        """Calculate spectrum kurtosis."""
        mean = np.average(self.uniform_wavelengths, weights=spectrum)
        variance = np.average((self.uniform_wavelengths - mean)**2, weights=spectrum)
        kurtosis = np.average((self.uniform_wavelengths - mean)**4, weights=spectrum)
        return kurtosis / variance**2 if variance > 0 else 0.0 
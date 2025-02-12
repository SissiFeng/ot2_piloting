# 需要实现：app/core/analysis/experiment_analyzer.py
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import logging
from uuid import UUID
from scipy import signal
from scipy.stats import norm
import json

from ..storage.models import Experiment, Well, MLAnalysis
from ..etl.transformations import SpectralDataTransformer

logger = logging.getLogger(__name__)

class ExperimentAnalyzer:
    """Analyzer for experiment results with visualization capabilities."""
    
    def __init__(self):
        """Initialize analyzer with spectral transformer."""
        self.spectral_transformer = SpectralDataTransformer()
    
    async def analyze_results(self, experiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze experiment results comprehensively.
        
        Args:
            experiment_data: Raw experiment data
            
        Returns:
            Dict containing analysis results
        """
        try:
            # Extract spectral data
            spectral_data = experiment_data.get("spectral_data", {})
            wavelengths = spectral_data.get("wavelengths", [])
            intensities = spectral_data.get("intensities", [])
            
            if not wavelengths or not intensities:
                raise ValueError("Missing spectral data")
            
            # Convert to numpy arrays
            wavelengths = np.array(wavelengths)
            intensities = np.array(intensities)
            
            # Perform analysis
            peak_analysis = self._analyze_peaks(wavelengths, intensities)
            statistical_analysis = self._calculate_statistics(intensities)
            quality_metrics = self._calculate_quality_metrics(intensities)
            
            # Generate visualizations
            plots = self._generate_plots(wavelengths, intensities)
            
            # Combine results
            analysis_results = {
                "peak_analysis": peak_analysis,
                "statistical_analysis": statistical_analysis,
                "quality_metrics": quality_metrics,
                "plots": plots,
                "timestamp": datetime.now().isoformat()
            }
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            raise
    
    def _analyze_peaks(self, wavelengths: np.ndarray, intensities: np.ndarray) -> Dict[str, Any]:
        """Analyze spectral peaks.
        
        Args:
            wavelengths: Array of wavelengths
            intensities: Array of intensity values
            
        Returns:
            Dict containing peak analysis results
        """
        # Find peaks
        peaks, properties = signal.find_peaks(intensities, 
                                            height=0.1,
                                            distance=20,
                                            prominence=0.1)
        
        # Calculate peak properties
        peak_results = []
        for i, peak_idx in enumerate(peaks):
            peak_info = {
                "wavelength": wavelengths[peak_idx],
                "intensity": intensities[peak_idx],
                "prominence": properties["prominences"][i],
                "width": properties["widths"][i],
                "left_base": wavelengths[int(properties["left_bases"][i])],
                "right_base": wavelengths[int(properties["right_bases"][i])]
            }
            peak_results.append(peak_info)
        
        return {
            "n_peaks": len(peaks),
            "peaks": peak_results,
            "dominant_peak": max(peak_results, key=lambda x: x["intensity"]) if peak_results else None
        }
    
    def _calculate_statistics(self, intensities: np.ndarray) -> Dict[str, float]:
        """Calculate statistical measures of spectral data.
        
        Args:
            intensities: Array of intensity values
            
        Returns:
            Dict containing statistical measures
        """
        return {
            "mean": float(np.mean(intensities)),
            "std": float(np.std(intensities)),
            "max": float(np.max(intensities)),
            "min": float(np.min(intensities)),
            "median": float(np.median(intensities)),
            "skewness": float(self._calculate_skewness(intensities)),
            "kurtosis": float(self._calculate_kurtosis(intensities))
        }
    
    def _calculate_quality_metrics(self, intensities: np.ndarray) -> Dict[str, float]:
        """Calculate quality metrics for the spectrum.
        
        Args:
            intensities: Array of intensity values
            
        Returns:
            Dict containing quality metrics
        """
        # Calculate signal-to-noise ratio
        noise = np.std(intensities[:100])  # Use first 100 points as noise estimate
        signal = np.max(intensities) - np.mean(intensities[:100])
        snr = signal / noise if noise > 0 else 0
        
        # Calculate other metrics
        return {
            "signal_to_noise": float(snr),
            "dynamic_range": float(np.max(intensities) / (np.min(intensities) + 1e-10)),
            "baseline_stability": float(np.std(intensities[:100]) / np.mean(intensities[:100])),
            "smoothness": float(self._calculate_smoothness(intensities))
        }
    
    def _generate_plots(self, wavelengths: np.ndarray, intensities: np.ndarray) -> Dict[str, Any]:
        """Generate visualization plots.
        
        Args:
            wavelengths: Array of wavelengths
            intensities: Array of intensity values
            
        Returns:
            Dict containing plot data
        """
        # Main spectrum plot
        spectrum_fig = go.Figure()
        spectrum_fig.add_trace(go.Scatter(
            x=wavelengths,
            y=intensities,
            mode='lines',
            name='Spectrum'
        ))
        spectrum_fig.update_layout(
            title="Absorption Spectrum",
            xaxis_title="Wavelength (nm)",
            yaxis_title="Intensity"
        )
        
        # Distribution plot
        hist_fig = go.Figure()
        hist_fig.add_trace(go.Histogram(
            x=intensities,
            nbinsx=50,
            name='Intensity Distribution'
        ))
        hist_fig.update_layout(
            title="Intensity Distribution",
            xaxis_title="Intensity",
            yaxis_title="Count"
        )
        
        return {
            "spectrum_plot": spectrum_fig.to_json(),
            "distribution_plot": hist_fig.to_json()
        }
    
    def _calculate_skewness(self, data: np.ndarray) -> float:
        """Calculate skewness of the data."""
        mean = np.mean(data)
        std = np.std(data)
        skewness = np.mean(((data - mean) / std) ** 3) if std > 0 else 0
        return skewness
    
    def _calculate_kurtosis(self, data: np.ndarray) -> float:
        """Calculate kurtosis of the data."""
        mean = np.mean(data)
        std = np.std(data)
        kurtosis = np.mean(((data - mean) / std) ** 4) - 3 if std > 0 else 0
        return kurtosis
    
    def _calculate_smoothness(self, data: np.ndarray) -> float:
        """Calculate smoothness metric using second derivative."""
        second_derivative = np.diff(data, n=2)
        smoothness = 1.0 / (1.0 + np.std(second_derivative))
        return smoothness
    
    async def generate_report(self, experiment_data: Dict[str, Any], 
                            analysis_results: Dict[str, Any]) -> str:
        """Generate analysis report in markdown format.
        
        Args:
            experiment_data: Raw experiment data
            analysis_results: Analysis results
            
        Returns:
            str: Markdown formatted report
        """
        try:
            # Extract key information
            exp_id = experiment_data.get("id", "Unknown")
            timestamp = experiment_data.get("created_at", datetime.now()).isoformat()
            
            # Generate report sections
            report_sections = [
                f"# Experiment Analysis Report\n",
                f"## Experiment Information\n",
                f"- Experiment ID: {exp_id}",
                f"- Date: {timestamp}",
                f"- Status: {experiment_data.get('status', 'Unknown')}\n",
                
                "## Peak Analysis\n",
                f"- Number of peaks: {analysis_results['peak_analysis']['n_peaks']}",
                "### Dominant Peak:",
                f"- Wavelength: {analysis_results['peak_analysis']['dominant_peak']['wavelength']:.2f} nm",
                f"- Intensity: {analysis_results['peak_analysis']['dominant_peak']['intensity']:.2f}\n",
                
                "## Statistical Analysis\n",
                f"- Mean Intensity: {analysis_results['statistical_analysis']['mean']:.2f}",
                f"- Standard Deviation: {analysis_results['statistical_analysis']['std']:.2f}",
                f"- Dynamic Range: {analysis_results['quality_metrics']['dynamic_range']:.2f}",
                f"- Signal-to-Noise Ratio: {analysis_results['quality_metrics']['signal_to_noise']:.2f}\n",
                
                "## Quality Metrics\n",
                f"- Baseline Stability: {analysis_results['quality_metrics']['baseline_stability']:.2f}",
                f"- Smoothness: {analysis_results['quality_metrics']['smoothness']:.2f}\n",
                
                "## Visualizations\n",
                "Plots are available in the analysis results as interactive Plotly figures."
            ]
            
            return "\n".join(report_sections)
            
        except Exception as e:
            logger.error(f"Report generation failed: {str(e)}")
            raise

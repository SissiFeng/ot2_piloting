"""ETL pipeline for experiment data processing."""
from typing import Dict, List, Optional, Any, Union
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from uuid import UUID
import asyncio
from prefect import task, Flow
from prefect.utilities.logging import get_logger
import subprocess
import os

from ..storage.models import (
    DataTransformation, ETLJob, DataQualityCheck,
    DataVersion, ProcessingStepType, DataFormat
)
from ..etl.transformations import SpectralDataTransformer

logger = get_logger()

class DataPipeline:
    """ETL pipeline for processing experimental data."""
    
    def __init__(self, db_manager=None, dbt_project_dir="dbt"):
        """Initialize pipeline with database manager."""
        self.db_manager = db_manager
        self.spectral_transformer = SpectralDataTransformer()
        self.dbt_project_dir = dbt_project_dir
        
    @task(retries=3, retry_delay_seconds=1)
    async def extract_data(self, 
                         experiment_id: UUID,
                         data_format: DataFormat = DataFormat.JSON) -> Dict[str, Any]:
        """Extract raw data from various sources.
        
        Args:
            experiment_id: ID of experiment to extract data from
            data_format: Format of the data to extract
            
        Returns:
            Dictionary containing extracted data
        """
        try:
            # Get experiment data from database
            experiment = await self.db_manager.get_experiment_with_details(experiment_id)
            if not experiment:
                raise ValueError(f"Experiment {experiment_id} not found")
                
            # Extract raw data from storage locations
            raw_data = {}
            for location in experiment.raw_data_locations:
                if location.data_format == data_format:
                    data = await self._read_data_from_location(location)
                    raw_data[location.file_path] = data
                    
            return {
                'experiment_id': experiment_id,
                'raw_data': raw_data,
                'metadata': experiment.metadata,
                'conditions': [dict(c) for c in experiment.conditions]
            }
            
        except Exception as e:
            logger.error(f"Error extracting data: {str(e)}")
            raise
            
    @task
    async def transform_data(self, 
                           extracted_data: Dict[str, Any],
                           processing_steps: Optional[List[ProcessingStepType]] = None) -> Dict[str, Any]:
        """Transform extracted data through processing pipeline.
        
        Args:
            extracted_data: Data from extraction step
            processing_steps: List of processing steps to apply
            
        Returns:
            Dictionary containing transformed data
        """
        try:
            if processing_steps is None:
                processing_steps = [
                    ProcessingStepType.BACKGROUND_SUBTRACTION,
                    ProcessingStepType.NORMALIZATION,
                    ProcessingStepType.FEATURE_EXTRACTION
                ]
                
            transformed_data = {}
            transformations = []
            
            for step in processing_steps:
                # Create transformation record
                transformation = DataTransformation(
                    name=f"{step.value}_transform",
                    type=step,
                    description=f"Apply {step.value} transformation",
                    parameters={},
                    code_version="v1.0",
                    environment={},
                    created_at=datetime.utcnow(),
                    created_by=UUID('00000000-0000-0000-0000-000000000000'),  # System
                    execution_time_ms=0,
                    input_checksums={},
                    output_checksums={}
                )
                
                # Process each spectrum
                start_time = datetime.utcnow()
                for path, data in extracted_data['raw_data'].items():
                    if 'spectrum' in data:
                        transformed_data[path] = await self._apply_transformation(
                            data,
                            step,
                            extracted_data['metadata']
                        )
                        
                # Update transformation record
                end_time = datetime.utcnow()
                transformation.execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
                transformations.append(transformation)
                
            return {
                'experiment_id': extracted_data['experiment_id'],
                'transformed_data': transformed_data,
                'transformations': transformations,
                'metadata': extracted_data['metadata']
            }
            
        except Exception as e:
            logger.error(f"Error transforming data: {str(e)}")
            raise
            
    @task
    async def validate_data(self, 
                          transformed_data: Dict[str, Any],
                          validation_rules: Optional[Dict[str, Any]] = None) -> List[DataQualityCheck]:
        """Validate transformed data quality.
        
        Args:
            transformed_data: Data from transformation step
            validation_rules: Custom validation rules
            
        Returns:
            List of quality check results
        """
        try:
            if validation_rules is None:
                validation_rules = {
                    'completeness': {'threshold': 0.95},
                    'value_range': {'min': 0, 'max': 1},
                    'outliers': {'std_dev': 3}
                }
                
            quality_checks = []
            
            for path, data in transformed_data['transformed_data'].items():
                # Check data completeness
                completeness = self._check_completeness(data)
                quality_checks.append(DataQualityCheck(
                    id=UUID('00000000-0000-0000-0000-000000000000'),
                    data_id=transformed_data['experiment_id'],
                    check_type='completeness',
                    check_name='Data completeness check',
                    parameters=validation_rules['completeness'],
                    result=completeness >= validation_rules['completeness']['threshold'],
                    details={'completeness_score': completeness},
                    created_at=datetime.utcnow(),
                    severity='error' if completeness < validation_rules['completeness']['threshold'] else 'info'
                ))
                
                # Check value ranges
                range_check = self._check_value_range(
                    data,
                    validation_rules['value_range']['min'],
                    validation_rules['value_range']['max']
                )
                quality_checks.append(DataQualityCheck(
                    id=UUID('00000000-0000-0000-0000-000000000000'),
                    data_id=transformed_data['experiment_id'],
                    check_type='value_range',
                    check_name='Value range check',
                    parameters=validation_rules['value_range'],
                    result=range_check['valid'],
                    details=range_check['details'],
                    created_at=datetime.utcnow(),
                    severity='error' if not range_check['valid'] else 'info'
                ))
                
                # Check for outliers
                outliers = self._check_outliers(data, validation_rules['outliers']['std_dev'])
                quality_checks.append(DataQualityCheck(
                    id=UUID('00000000-0000-0000-0000-000000000000'),
                    data_id=transformed_data['experiment_id'],
                    check_type='outliers',
                    check_name='Outlier detection',
                    parameters=validation_rules['outliers'],
                    result=outliers['valid'],
                    details=outliers['details'],
                    created_at=datetime.utcnow(),
                    severity='warning' if not outliers['valid'] else 'info'
                ))
                
            return quality_checks
            
        except Exception as e:
            logger.error(f"Error validating data: {str(e)}")
            raise
            
    @task
    async def load_data(self,
                       transformed_data: Dict[str, Any],
                       quality_checks: List[DataQualityCheck]) -> ETLJob:
        """Load transformed and validated data into storage.
        
        Args:
            transformed_data: Validated data to load
            quality_checks: Results of quality validation
            
        Returns:
            ETL job record
        """
        try:
            # Check if data passed validation
            failed_checks = [check for check in quality_checks 
                           if not check.result and check.severity == 'error']
            if failed_checks:
                raise ValueError(f"Data failed {len(failed_checks)} critical quality checks")
                
            # Create ETL job record
            job = ETLJob(
                id=UUID('00000000-0000-0000-0000-000000000000'),
                job_name=f"process_experiment_{transformed_data['experiment_id']}",
                status="running",
                start_time=datetime.utcnow(),
                source_data_ids=[transformed_data['experiment_id']],
                target_data_ids=[],
                transformations=transformed_data['transformations'],
                performance_metrics={}
            )
            
            try:
                # Save transformed data
                for path, data in transformed_data['transformed_data'].items():
                    target_id = await self._save_transformed_data(
                        data,
                        transformed_data['experiment_id'],
                        path
                    )
                    job.target_data_ids.append(target_id)
                    
                # Update job status
                job.status = "completed"
                job.end_time = datetime.utcnow()
                job.performance_metrics = {
                    'processing_time_ms': int((job.end_time - job.start_time).total_seconds() * 1000),
                    'quality_checks_passed': len([c for c in quality_checks if c.result]),
                    'quality_checks_failed': len([c for c in quality_checks if not c.result])
                }
                
            except Exception as e:
                job.status = "failed"
                job.end_time = datetime.utcnow()
                job.error_message = str(e)
                raise
                
            finally:
                if self.db_manager:
                    await self.db_manager.update_etl_job(job)
                    
            return job
            
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            raise
            
    @task
    async def run_dbt_models(self, 
                            models: Optional[List[str]] = None,
                            exclude: Optional[List[str]] = None) -> bool:
        """Run dbt models for data transformation.
        
        Args:
            models: Optional list of specific models to run
            exclude: Optional list of models to exclude
            
        Returns:
            Boolean indicating success
        """
        try:
            cmd = ["dbt", "run", "--project-dir", self.dbt_project_dir]
            
            if models:
                cmd.extend(["--select", " ".join(models)])
            if exclude:
                cmd.extend(["--exclude", " ".join(exclude)])
                
            # Run dbt command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"dbt run output: {result.stdout}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"dbt run failed: {e.stderr}")
            raise
            
    @task
    async def run_dbt_tests(self) -> bool:
        """Run dbt tests to validate data quality.
        
        Returns:
            Boolean indicating all tests passed
        """
        try:
            cmd = ["dbt", "test", "--project-dir", self.dbt_project_dir]
            
            # Run dbt tests
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"dbt test output: {result.stdout}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"dbt tests failed: {e.stderr}")
            raise
            
    @task
    async def generate_dbt_docs(self) -> str:
        """Generate dbt documentation.
        
        Returns:
            Path to generated documentation
        """
        try:
            cmd = ["dbt", "docs", "generate", "--project-dir", self.dbt_project_dir]
            
            # Generate documentation
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"dbt docs output: {result.stdout}")
            return os.path.join(self.dbt_project_dir, "target", "index.html")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"dbt docs generation failed: {e.stderr}")
            raise
            
    async def run_pipeline(self,
                          experiment_id: UUID,
                          processing_steps: Optional[List[ProcessingStepType]] = None,
                          validation_rules: Optional[Dict[str, Any]] = None) -> ETLJob:
        """Run complete ETL pipeline for experiment data.
        
        Args:
            experiment_id: ID of experiment to process
            processing_steps: Custom processing steps
            validation_rules: Custom validation rules
            
        Returns:
            Completed ETL job record
        """
        async with Flow("experiment_etl") as flow:
            # Extract data
            extracted = await self.extract_data(experiment_id)
            
            # Transform data using dbt
            dbt_success = await self.run_dbt_models(
                models=["staging", "intermediate", "mart"]
            )
            
            if not dbt_success:
                raise ValueError("dbt transformation failed")
                
            # Run data quality tests
            test_success = await self.run_dbt_tests()
            if not test_success:
                raise ValueError("dbt tests failed")
                
            # Generate documentation
            docs_path = await self.generate_dbt_docs()
            
            # Additional transformations if needed
            transformed = await self.transform_data(extracted, processing_steps)
            
            # Validate data
            quality_checks = await self.validate_data(transformed, validation_rules)
            
            # Load data
            job = await self.load_data(transformed, quality_checks)
            
        return job
        
    async def _read_data_from_location(self, location: Any) -> Dict[str, Any]:
        """Read data from storage location."""
        # Implement actual data reading logic
        pass
        
    async def _apply_transformation(self,
                                  data: Dict[str, Any],
                                  step: ProcessingStepType,
                                  metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Apply transformation step to data."""
        if step == ProcessingStepType.BACKGROUND_SUBTRACTION:
            return self.spectral_transformer.preprocess_spectrum(
                data['wavelengths'],
                data['intensities'],
                remove_background=True,
                normalize=False
            )
        elif step == ProcessingStepType.NORMALIZATION:
            return self.spectral_transformer.preprocess_spectrum(
                data['wavelengths'],
                data['intensities'],
                remove_background=False,
                normalize=True
            )
        elif step == ProcessingStepType.FEATURE_EXTRACTION:
            return self.spectral_transformer.extract_features(data['spectrum'])
        else:
            raise ValueError(f"Unsupported transformation step: {step}")
            
    async def _save_transformed_data(self,
                                   data: Dict[str, Any],
                                   experiment_id: UUID,
                                   path: str) -> UUID:
        """Save transformed data to storage."""
        # Implement actual data saving logic
        pass
        
    def _check_completeness(self, data: Dict[str, Any]) -> float:
        """Check data completeness."""
        if isinstance(data, dict):
            total_fields = len(data)
            non_null_fields = sum(1 for v in data.values() if v is not None)
            return non_null_fields / total_fields
        elif isinstance(data, (np.ndarray, list)):
            return 1 - (np.isnan(data).sum() / len(data))
        return 1.0
        
    def _check_value_range(self,
                          data: Union[Dict[str, Any], np.ndarray],
                          min_value: float,
                          max_value: float) -> Dict[str, Any]:
        """Check if values are within expected range."""
        if isinstance(data, dict):
            values = np.array([v for v in data.values() if isinstance(v, (int, float))])
        else:
            values = np.array(data)
            
        in_range = (values >= min_value) & (values <= max_value)
        return {
            'valid': in_range.all(),
            'details': {
                'out_of_range_count': (~in_range).sum(),
                'min_value': float(values.min()),
                'max_value': float(values.max())
            }
        }
        
    def _check_outliers(self,
                       data: Union[Dict[str, Any], np.ndarray],
                       std_dev: float) -> Dict[str, Any]:
        """Check for outliers using standard deviation method."""
        if isinstance(data, dict):
            values = np.array([v for v in data.values() if isinstance(v, (int, float))])
        else:
            values = np.array(data)
            
        mean = np.mean(values)
        std = np.std(values)
        z_scores = np.abs((values - mean) / std)
        outliers = z_scores > std_dev
        
        return {
            'valid': not outliers.any(),
            'details': {
                'outlier_count': outliers.sum(),
                'outlier_indices': np.where(outliers)[0].tolist(),
                'z_scores': z_scores[outliers].tolist()
            }
        }

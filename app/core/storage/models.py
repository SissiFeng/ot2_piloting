"""Database models for the application."""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple, Set
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl, validator


class DataStorageType(str, Enum):
    """Storage type for experimental data."""
    S3 = "s3"
    LOCAL = "local"
    MONGODB = "mongodb"


class DataFormat(str, Enum):
    """Data format for experimental data."""
    CSV = "csv"
    JSON = "json"
    PARQUET = "parquet"
    SPECTRAL = "spectral"
    IMAGE = "image"


class ExperimentalCondition(BaseModel):
    """Experimental condition model."""
    temperature: float
    humidity: float
    pressure: Optional[float] = None
    light_intensity: Optional[float] = None
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class DataLineageType(str, Enum):
    """Data lineage relationship types."""
    DERIVED_FROM = "derived_from"
    TRANSFORMED_BY = "transformed_by"
    VALIDATED_BY = "validated_by"
    AGGREGATED_FROM = "aggregated_from"
    FILTERED_FROM = "filtered_from"
    MERGED_WITH = "merged_with"


class ProcessingStepType(str, Enum):
    """Types of data processing steps."""
    RAW_CAPTURE = "raw_capture"
    BACKGROUND_SUBTRACTION = "background_subtraction"
    NORMALIZATION = "normalization"
    FEATURE_EXTRACTION = "feature_extraction"
    OUTLIER_DETECTION = "outlier_detection"
    SMOOTHING = "smoothing"
    PEAK_DETECTION = "peak_detection"
    INTEGRATION = "integration"
    TRANSFORMATION = "transformation"
    VALIDATION = "validation"


class DataVersion(BaseModel):
    """Data version model."""
    version_id: str
    created_at: datetime
    created_by: UUID
    parent_version_id: Optional[str] = None
    processing_step: ProcessingStepType
    parameters: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    quality_metrics: Optional[Dict[str, float]] = None
    validation_status: Optional[str] = None


class DataLineage(BaseModel):
    """Data lineage relationship model."""
    source_id: UUID
    target_id: UUID
    relationship_type: DataLineageType
    transformation_id: Optional[UUID] = None
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class DataTransformation(BaseModel):
    """Data transformation record model."""
    id: UUID
    name: str
    type: ProcessingStepType
    description: str
    parameters: Dict[str, Any]
    code_version: str
    git_commit: Optional[str] = None
    environment: Dict[str, str]
    created_at: datetime
    created_by: UUID
    execution_time_ms: int
    input_checksums: Dict[str, str]
    output_checksums: Dict[str, str]
    metadata: Optional[Dict[str, Any]] = None


class ETLJob(BaseModel):
    """ETL job execution record."""
    id: UUID
    job_name: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    source_data_ids: List[UUID]
    target_data_ids: List[UUID]
    transformations: List[DataTransformation]
    error_message: Optional[str] = None
    performance_metrics: Optional[Dict[str, float]] = None
    metadata: Optional[Dict[str, Any]] = None


class RawDataLocation(BaseModel):
    """Raw data storage location model."""
    storage_type: DataStorageType
    data_format: DataFormat
    bucket_name: Optional[str] = None
    file_path: str
    version_id: Optional[str] = None
    size_bytes: Optional[int] = None
    md5_hash: Optional[str] = None
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    # Data versioning and lineage
    version: DataVersion
    parent_locations: List[UUID] = []
    processing_history: List[DataTransformation] = []
    quality_metrics: Dict[str, float] = {}
    validation_status: str = "pending"
    
    @validator('validation_status')
    def validate_status(cls, v):
        allowed_statuses = {'pending', 'validated', 'rejected', 'needs_review'}
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of {allowed_statuses}')
        return v


class ExperimentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    REVIEWED = "reviewed"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PlateType(BaseModel):
    """Plate type model for different experimental setups."""
    id: Optional[UUID] = None
    name: str
    wells_count: int
    well_volume_ul: float
    well_dimensions: Dict[str, float]  # height, diameter, etc.
    material: str
    manufacturer: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class QueryType(str, Enum):
    """Types of data queries."""
    EXACT = "exact"
    RANGE = "range"
    REGEX = "regex"
    FUZZY = "fuzzy"
    SEMANTIC = "semantic"
    AGGREGATE = "aggregate"


class DataStreamType(str, Enum):
    """Types of data streams."""
    BATCH = "batch"
    REAL_TIME = "real_time"
    INCREMENTAL = "incremental"
    SNAPSHOT = "snapshot"


class DataQueryFilter(BaseModel):
    """Data query filter model."""
    field: str
    operator: str
    value: Any
    query_type: QueryType = QueryType.EXACT
    fuzzy_threshold: Optional[float] = None
    case_sensitive: bool = True
    metadata: Optional[Dict[str, Any]] = None


class DataQuery(BaseModel):
    """Data query model."""
    filters: List[DataQueryFilter]
    sort_by: Optional[List[str]] = None
    sort_order: Optional[List[str]] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    include_fields: Optional[List[str]] = None
    exclude_fields: Optional[List[str]] = None
    aggregations: Optional[List[Dict[str, Any]]] = None
    stream_type: DataStreamType = DataStreamType.BATCH
    cache_ttl: Optional[int] = None  # seconds
    
    @validator('sort_order')
    def validate_sort_order(cls, v):
        if v is not None:
            allowed_orders = {'asc', 'desc'}
            if not all(order in allowed_orders for order in v):
                raise ValueError(f'Sort order must be one of {allowed_orders}')
        return v


class MLFeatureSet(BaseModel):
    """ML feature set definition."""
    id: UUID
    name: str
    version: str
    features: List[str]
    transformations: List[DataTransformation]
    data_dependencies: List[UUID]  # References to required data sources
    update_frequency: str  # cron expression
    last_updated: datetime
    metadata: Optional[Dict[str, Any]] = None


class MLModelInput(BaseModel):
    """ML model input specification."""
    feature_sets: List[MLFeatureSet]
    data_query: DataQuery
    preprocessing_steps: List[ProcessingStepType]
    validation_rules: Optional[Dict[str, Any]] = None
    batch_size: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class MLModelOutput(BaseModel):
    """ML model output specification."""
    id: UUID
    model_version: str
    input_id: UUID
    predictions: Dict[str, Any]
    confidence_scores: Optional[Dict[str, float]] = None
    execution_time_ms: int
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class StreamingConfig(BaseModel):
    """Data streaming configuration."""
    stream_id: UUID
    stream_type: DataStreamType
    query: DataQuery
    batch_size: Optional[int] = None
    interval_seconds: Optional[int] = None
    max_retries: int = 3
    retry_delay_seconds: int = 5
    error_handling: Dict[str, Any] = {}
    metadata: Optional[Dict[str, Any]] = None


class CacheConfig(BaseModel):
    """Cache configuration for data queries."""
    enabled: bool = True
    ttl_seconds: int = 3600
    max_size_mb: int = 1000
    eviction_policy: str = "lru"
    compression_enabled: bool = True
    metadata: Optional[Dict[str, Any]] = None


class MLAnalysis(BaseModel):
    """Machine Learning analysis results model."""
    id: Optional[UUID] = None
    experiment_id: UUID
    model_version: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    confidence_scores: Optional[Dict[str, float]] = None
    review_status: ReviewStatus = ReviewStatus.PENDING
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    # Optimization related fields
    optimization_history: List[OptimizationResult] = []
    best_parameters: Optional[Dict[str, float]] = None
    convergence_status: str = "pending"
    optimization_metrics: Optional[Dict[str, float]] = None
    target_spectrum: Optional[List[float]] = None
    wavelength_range: Optional[Tuple[float, float]] = None
    optimization_constraints: Optional[Dict[str, Any]] = None
    acquisition_function: Optional[str] = None
    
    # ML Integration
    feature_sets: List[MLFeatureSet] = []
    model_inputs: List[MLModelInput] = []
    model_outputs: List[MLModelOutput] = []
    streaming_configs: List[StreamingConfig] = []
    cache_config: Optional[CacheConfig] = None
    
    def add_feature_set(self, feature_set: MLFeatureSet):
        """Add new feature set with validation."""
        existing_names = {fs.name for fs in self.feature_sets}
        if feature_set.name in existing_names:
            raise ValueError(f"Feature set {feature_set.name} already exists")
        self.feature_sets.append(feature_set)
    
    def get_latest_predictions(self) -> Optional[MLModelOutput]:
        """Get the latest model predictions."""
        if not self.model_outputs:
            return None
        return max(self.model_outputs, key=lambda x: x.created_at)


class Experiment(BaseModel):
    """Experiment model with enhanced data structure."""
    id: Optional[UUID] = None
    user_id: UUID
    plate_type_id: UUID
    status: ExperimentStatus
    
    # Raw data storage
    raw_data_locations: List[RawDataLocation] = []
    
    # Experimental conditions
    conditions: List[ExperimentalCondition] = []
    
    # OT-2 specific metadata
    ot2_device_id: str
    ot2_protocol_id: str
    ot2_firmware_version: str
    pipette_configurations: Dict[str, Any]
    
    # General metadata
    metadata: Dict[str, Any]
    protocol_data: Optional[Dict[str, Any]] = None
    results_data: Optional[Dict[str, Any]] = None
    
    # Timing information
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_modified_at: Optional[datetime] = None
    
    # Error handling
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    
    # Database references
    mongo_id: Optional[str] = None
    s3_base_path: Optional[str] = None
    
    # Data lineage tracking
    data_versions: List[DataVersion] = []
    lineage_relationships: List[DataLineage] = []
    etl_jobs: List[ETLJob] = []
    processing_history: List[DataTransformation] = []
    
    # ML Integration
    feature_sets: List[MLFeatureSet] = []
    model_inputs: List[MLModelInput] = []
    model_outputs: List[MLModelOutput] = []
    streaming_configs: List[StreamingConfig] = []
    cache_config: Optional[CacheConfig] = None
    
    def add_data_version(self, version: DataVersion):
        """Add new data version with validation."""
        if not self.data_versions:
            if version.parent_version_id is not None:
                raise ValueError("First version cannot have parent")
        else:
            if version.parent_version_id is None:
                raise ValueError("Non-first version must have parent")
        self.data_versions.append(version)
    
    def add_lineage_relationship(self, relationship: DataLineage):
        """Add lineage relationship with validation."""
        existing_ids = {r.target_id for r in self.lineage_relationships}
        if relationship.target_id in existing_ids:
            raise ValueError(f"Target ID {relationship.target_id} already exists")
        self.lineage_relationships.append(relationship)
    
    def get_ml_ready_data(self, feature_set_id: UUID) -> Dict[str, Any]:
        """Get data prepared for ML processing."""
        feature_set = next((fs for fs in self.feature_sets if fs.id == feature_set_id), None)
        if not feature_set:
            raise ValueError(f"Feature set {feature_set_id} not found")
            
        # Collect and transform data according to feature set specification
        data = {}
        for feature in feature_set.features:
            # Apply transformations and collect data
            transformed_data = self._apply_transformations(feature, feature_set.transformations)
            data[feature] = transformed_data
        return data
    
    def _apply_transformations(self, feature: str, transformations: List[DataTransformation]) -> Any:
        """Apply transformations to feature data."""
        # Implementation of data transformation logic
        pass


class Well(BaseModel):
    """Well model with enhanced data structure."""
    id: Optional[UUID] = None
    experiment_id: UUID
    well_id: str
    status: str
    
    # Raw data storage
    raw_data_locations: List[RawDataLocation] = []
    
    # Well-specific metadata
    position: Dict[str, int]  # row, column
    volume_ul: float
    components: Dict[str, float]  # component concentrations
    metadata: Dict[str, Any]
    
    # Measurement data
    measurement_data: Optional[Dict[str, Any]] = None
    analysis_results: Optional[Dict[str, Any]] = None
    
    # Timing information
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    measured_at: Optional[datetime] = None
    
    # Database references
    mongo_id: Optional[str] = None
    
    # Data lineage tracking
    data_versions: List[DataVersion] = []
    lineage_relationships: List[DataLineage] = []
    processing_history: List[DataTransformation] = []
    quality_metrics: Dict[str, float] = {}
    
    # ML Integration
    feature_sets: List[MLFeatureSet] = []
    model_outputs: List[MLModelOutput] = []
    
    def get_latest_measurement(self) -> Optional[Dict[str, Any]]:
        """Get the latest measurement data with ML predictions."""
        if not self.measurement_data:
            return None
            
        result = self.measurement_data.copy()
        if self.model_outputs:
            latest_prediction = max(self.model_outputs, key=lambda x: x.created_at)
            result['ml_predictions'] = latest_prediction.predictions
            result['confidence_scores'] = latest_prediction.confidence_scores
        return result


class OptimizationResult(BaseModel):
    """Optimization result model."""
    iteration: int
    parameters: Dict[str, float]
    objective_value: float
    metrics: Dict[str, float]
    predicted_mean: float
    predicted_std: float
    acquisition_value: float
    created_at: Optional[datetime] = None


class ExperimentWithDetails(Experiment):
    """Experiment model with additional details."""
    plate_type: PlateType
    wells: List[Well]
    ml_analysis: Optional[MLAnalysis] = None


class AuditLog(BaseModel):
    """Enhanced audit log model for tracking changes."""
    id: Optional[UUID] = None
    table_name: str
    record_id: UUID
    action: str
    old_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    user_id: UUID
    created_at: Optional[datetime] = None
    
    # Enhanced auditing
    change_reason: Optional[str] = None
    change_type: str  # schema, data, permission, etc.
    source_system: str  # UI, API, ETL, etc.
    ip_address: Optional[str] = None
    session_id: Optional[str] = None
    transaction_id: Optional[UUID] = None
    affected_fields: List[str] = []
    severity: str = "info"
    related_records: Dict[str, UUID] = {}
    
    @validator('severity')
    def validate_severity(cls, v):
        allowed_severities = {'info', 'warning', 'error', 'critical'}
        if v not in allowed_severities:
            raise ValueError(f'Severity must be one of {allowed_severities}')
        return v


class DataQualityCheck(BaseModel):
    """Data quality check results."""
    id: UUID
    data_id: UUID
    check_type: str
    check_name: str
    parameters: Dict[str, Any]
    result: bool
    details: Dict[str, Any]
    created_at: datetime
    severity: str
    metadata: Optional[Dict[str, Any]] = None 
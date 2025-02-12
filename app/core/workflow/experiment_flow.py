from prefect import flow, task, get_run_logger
from prefect.tasks import task_input_hash
from datetime import timedelta
import time
from typing import Dict, Any, Optional
from ..storage.db_manager import DatabaseManager
from prometheus_client import Counter, Histogram, Gauge

# Prometheus metrics
EXPERIMENT_COUNTER = Counter(
    'ot2_experiments_total',
    'Total number of experiments',
    ['status']
)

EXPERIMENT_DURATION = Histogram(
    'ot2_experiment_duration_seconds',
    'Time spent processing experiment',
    ['step']
)

DB_WRITE_LATENCY = Histogram(
    'ot2_db_write_latency_seconds',
    'Database write latency',
    ['database', 'operation']
)

ACTIVE_EXPERIMENTS = Gauge(
    'ot2_active_experiments',
    'Number of currently running experiments'
)

@task(cache_key_fn=task_input_hash, cache_expiration=timedelta(hours=1))
async def validate_experiment_params(params: Dict[str, Any]) -> bool:
    """Validate experiment parameters"""
    logger = get_run_logger()
    
    required_fields = ['user_id', 'well_id', 'colors']
    for field in required_fields:
        if field not in params:
            logger.error(f"Missing required field: {field}")
            return False
            
    return True

@task(retries=3)
async def prepare_experiment(db: DatabaseManager, params: Dict[str, Any]) -> str:
    """Prepare experiment in database"""
    with EXPERIMENT_DURATION.labels('preparation').time():
        experiment_id = await db.dual_write_experiment(
            params['user_id'],
            params
        )
        EXPERIMENT_COUNTER.labels(status='prepared').inc()
        return experiment_id

@task
async def run_ot2_operation(experiment_id: str, params: Dict[str, Any]) -> bool:
    """Execute OT2 operation"""
    logger = get_run_logger()
    ACTIVE_EXPERIMENTS.inc()
    
    try:
        with EXPERIMENT_DURATION.labels('ot2_operation').time():
            # Simulate OT2 operation
            time.sleep(5)  # Replace with actual OT2 operation
            logger.info(f"OT2 operation completed for experiment {experiment_id}")
            return True
    except Exception as e:
        logger.error(f"OT2 operation failed: {e}")
        EXPERIMENT_COUNTER.labels(status='failed').inc()
        raise
    finally:
        ACTIVE_EXPERIMENTS.dec()

@task
async def record_results(db: DatabaseManager, experiment_id: str, well_id: str, results: Dict[str, Any]) -> str:
    """Record experiment results"""
    with EXPERIMENT_DURATION.labels('recording').time():
        with DB_WRITE_LATENCY.labels('postgres', 'write').time():
            result_id = await db.dual_write_result(
                experiment_id,
                well_id,
                results
            )
        EXPERIMENT_COUNTER.labels(status='completed').inc()
        return result_id

@flow(name="OT2 Experiment Flow")
async def run_experiment(
    db: DatabaseManager,
    params: Dict[str, Any],
    retry_failed: bool = True
) -> Optional[str]:
    """Main experiment flow"""
    logger = get_run_logger()
    
    # Validate parameters
    is_valid = await validate_experiment_params(params)
    if not is_valid:
        EXPERIMENT_COUNTER.labels(status='invalid').inc()
        return None
    
    try:
        # Prepare experiment
        experiment_id = await prepare_experiment(db, params)
        
        # Run OT2 operation
        success = await run_ot2_operation(experiment_id, params)
        if not success:
            return None
            
        # Record results
        result_id = await record_results(
            db,
            experiment_id,
            params['well_id'],
            {'status': 'success', 'data': params}  # Replace with actual results
        )
        
        # Verify data consistency
        is_consistent = await db.verify_consistency('results', result_id)
        if not is_consistent and retry_failed:
            logger.warning(f"Data inconsistency detected for result {result_id}")
            await db.repair_inconsistency('results', result_id)
        
        return result_id
        
    except Exception as e:
        logger.error(f"Experiment failed: {e}")
        EXPERIMENT_COUNTER.labels(status='failed').inc()
        raise 
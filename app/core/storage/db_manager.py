"""Database manager for handling all database operations."""
from typing import Optional, Dict, Any, List
import asyncpg
import motor.motor_asyncio
from datetime import datetime, timedelta
import logging
from prefect import task, get_run_logger
from uuid import UUID

from .models import (
    PlateType, Experiment, Well, MLAnalysis,
    ExperimentWithDetails, AuditLog,
    ExperimentStatus, ReviewStatus
)
from ..auth.auth_manager import User, UserInDB, UserRole
import json

class DatabaseManager:
    """Database manager for handling all database operations."""
    
    def __init__(self, postgres_dsn: str, mongodb_uri: str):
        self.postgres_pool = None
        self.mongodb_client = None
        self.postgres_dsn = postgres_dsn
        self.mongodb_uri = mongodb_uri
        self.logger = logging.getLogger(__name__)

    async def connect(self):
        """Initialize database connections"""
        self.postgres_pool = await asyncpg.create_pool(self.postgres_dsn)
        self.mongodb_client = motor.motor_asyncio.AsyncIOMotorClient(self.mongodb_uri)

    async def close(self):
        """Close database connections"""
        if self.postgres_pool:
            await self.postgres_pool.close()
        if self.mongodb_client:
            self.mongodb_client.close()

    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """Get user by email from PostgreSQL"""
        async with self.postgres_pool.acquire() as conn:
            user_record = await conn.fetchrow("""
                SELECT id, email, role, hashed_password, quota_remaining, disabled
                FROM users
                WHERE email = $1
            """, email)
            
            if not user_record:
                return None
                
            return UserInDB(
                email=user_record['email'],
                role=UserRole(user_record['role']),
                disabled=user_record['disabled'],
                hashed_password=user_record['hashed_password']
            )

    async def get_user_experiments(self, email: str) -> List[Dict[str, Any]]:
        """Get experiments for a specific user"""
        async with self.postgres_pool.acquire() as conn:
            experiments = await conn.fetch("""
                SELECT e.id, e.status, e.created_at, e.completed_at,
                       w.well_id, e.metadata->>'red' as red,
                       e.metadata->>'yellow' as yellow,
                       e.metadata->>'blue' as blue
                FROM experiments e
                JOIN users u ON e.user_id = u.id
                LEFT JOIN wells w ON e.id = w.experiment_id
                WHERE u.email = $1
                ORDER BY e.created_at DESC
            """, email)
            
            return [dict(exp) for exp in experiments]

    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide metrics"""
        async with self.postgres_pool.acquire() as conn:
            # Get active experiments count
            active_count = await conn.fetchval("""
                SELECT COUNT(*) 
                FROM experiments 
                WHERE status = 'running'
            """)
            
            # Calculate success rate
            success_rate = await conn.fetchval("""
                WITH experiment_stats AS (
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE status = 'completed') as completed
                    FROM experiments
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                )
                SELECT 
                    CASE 
                        WHEN total > 0 THEN (completed::float / total * 100)
                        ELSE 0
                    END
                FROM experiment_stats
            """)
            
            # Calculate average duration
            avg_duration = await conn.fetchval("""
                SELECT 
                    EXTRACT(EPOCH FROM AVG(completed_at - started_at))
                FROM experiments
                WHERE status = 'completed'
                AND created_at > NOW() - INTERVAL '24 hours'
            """)
            
            return {
                "active_experiments": active_count,
                "success_rate": round(success_rate, 2) if success_rate else 0,
                "avg_duration": round(avg_duration, 2) if avg_duration else 0
            }

    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users (for admin panel)"""
        async with self.postgres_pool.acquire() as conn:
            users = await conn.fetch("""
                SELECT 
                    email,
                    role,
                    quota_remaining,
                    disabled,
                    created_at,
                    (
                        SELECT COUNT(*)
                        FROM experiments e
                        WHERE e.user_id = u.id
                    ) as experiment_count
                FROM users u
                ORDER BY created_at DESC
            """)
            
            return [dict(user) for user in users]

    @task(retries=3, retry_delay_seconds=1)
    async def dual_write_experiment(self, user_id: str, metadata: Dict[str, Any]) -> str:
        """Create experiment record with dual-write pattern"""
        logger = get_run_logger()
        
        # Start transaction in PostgreSQL
        async with self.postgres_pool.acquire() as conn:
            async with conn.transaction():
                # Check user quota
                remaining_quota = await conn.fetchval("""
                    SELECT quota_remaining
                    FROM users
                    WHERE id = $1
                    FOR UPDATE
                """, user_id)
                
                if remaining_quota <= 0:
                    raise ValueError("User has no remaining experiment quota")
                
                # Decrement quota
                await conn.execute("""
                    UPDATE users
                    SET quota_remaining = quota_remaining - 1
                    WHERE id = $1
                """, user_id)
                
                # Insert experiment
                experiment_id = await conn.fetchval("""
                    INSERT INTO experiments (user_id, status, metadata)
                    VALUES ($1, 'pending', $2)
                    RETURNING id
                """, user_id, metadata)

                try:
                    # Insert into MongoDB
                    mongo_result = await self.mongodb_client.experiments.insert_one({
                        "postgres_id": str(experiment_id),
                        "user_id": user_id,
                        "status": "pending",
                        "metadata": metadata,
                        "created_at": datetime.utcnow()
                    })

                    # Update PostgreSQL with MongoDB reference
                    await conn.execute("""
                        UPDATE experiments 
                        SET mongo_id = $1 
                        WHERE id = $2
                    """, str(mongo_result.inserted_id), experiment_id)

                except Exception as e:
                    logger.error(f"MongoDB write failed: {e}")
                    raise

        return str(experiment_id)

    @task(retries=3, retry_delay_seconds=1)
    async def dual_write_result(self, experiment_id: str, well_id: str, measurement_data: Dict[str, Any]) -> str:
        """Create result record with dual-write pattern"""
        logger = get_run_logger()

        async with self.postgres_pool.acquire() as conn:
            async with conn.transaction():
                # Insert into PostgreSQL
                result_id = await conn.fetchval("""
                    INSERT INTO results (experiment_id, well_id, measurement_data)
                    VALUES ($1, $2, $3)
                    RETURNING id
                """, experiment_id, well_id, measurement_data)

                try:
                    # Insert into MongoDB
                    mongo_result = await self.mongodb_client.results.insert_one({
                        "postgres_id": str(result_id),
                        "experiment_id": experiment_id,
                        "well_id": well_id,
                        "measurement_data": measurement_data,
                        "created_at": datetime.utcnow()
                    })

                    # Update PostgreSQL with MongoDB reference
                    await conn.execute("""
                        UPDATE results 
                        SET mongo_id = $1 
                        WHERE id = $2
                    """, str(mongo_result.inserted_id), result_id)

                except Exception as e:
                    logger.error(f"MongoDB write failed: {e}")
                    raise

        return str(result_id)

    async def verify_consistency(self, table_name: str, record_id: str) -> bool:
        """Verify data consistency between PostgreSQL and MongoDB"""
        async with self.postgres_pool.acquire() as conn:
            pg_record = await conn.fetchrow(f"""
                SELECT id, mongo_id FROM {table_name}
                WHERE id = $1
            """, record_id)

            if not pg_record:
                return False

            mongo_record = await self.mongodb_client[table_name].find_one({
                "postgres_id": str(record_id)
            })

            return bool(mongo_record and str(mongo_record["_id"]) == pg_record["mongo_id"])

    @task
    async def repair_inconsistency(self, table_name: str, record_id: str):
        """Repair data inconsistency between databases"""
        logger = get_run_logger()
        
        async with self.postgres_pool.acquire() as conn:
            pg_record = await conn.fetchrow(f"""
                SELECT * FROM {table_name}
                WHERE id = $1
            """, record_id)

            if not pg_record:
                logger.error(f"Record not found in PostgreSQL: {record_id}")
                return

            # Convert PostgreSQL record to dict
            pg_data = dict(pg_record)
            
            # Update or insert into MongoDB
            await self.mongodb_client[table_name].update_one(
                {"postgres_id": str(record_id)},
                {"$set": pg_data},
                upsert=True
            )

    async def get_experiment_statistics(self, time_range: str = '24h') -> Dict[str, Any]:
        """Get detailed experiment statistics
        
        Args:
            time_range: Time range for statistics ('24h', '7d', '30d')
        """
        time_intervals = {
            '24h': "INTERVAL '24 hours'",
            '7d': "INTERVAL '7 days'",
            '30d': "INTERVAL '30 days'"
        }
        interval = time_intervals.get(time_range, time_intervals['24h'])

        async with self.postgres_pool.acquire() as conn:
            # Success rate trend by hour/day
            success_trend = await conn.fetch(f"""
                WITH time_series AS (
                    SELECT generate_series(
                        date_trunc('hour', NOW() - {interval}),
                        date_trunc('hour', NOW()),
                        '1 hour'
                    ) as time_bucket
                ),
                experiment_stats AS (
                    SELECT 
                        date_trunc('hour', created_at) as hour,
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE status = 'completed') as completed
                    FROM experiments
                    WHERE created_at > NOW() - {interval}
                    GROUP BY hour
                )
                SELECT 
                    ts.time_bucket,
                    COALESCE(es.total, 0) as total,
                    COALESCE(es.completed, 0) as completed,
                    CASE 
                        WHEN COALESCE(es.total, 0) > 0 
                        THEN ROUND((COALESCE(es.completed, 0)::float / es.total * 100)::numeric, 2)
                        ELSE 0
                    END as success_rate
                FROM time_series ts
                LEFT JOIN experiment_stats es ON ts.time_bucket = es.hour
                ORDER BY ts.time_bucket
            """)

            # Common error patterns
            error_patterns = await conn.fetch("""
                SELECT 
                    error_message,
                    COUNT(*) as occurrence_count,
                    MIN(created_at) as first_occurrence,
                    MAX(created_at) as last_occurrence
                FROM experiments
                WHERE status = 'failed'
                AND created_at > NOW() - INTERVAL '30 days'
                GROUP BY error_message
                ORDER BY occurrence_count DESC
                LIMIT 10
            """)

            # Color combination statistics
            color_stats = await conn.fetch("""
                WITH color_ranges AS (
                    SELECT 
                        id,
                        CASE 
                            WHEN (metadata->>'red')::float > 60 THEN 'high'
                            WHEN (metadata->>'red')::float > 30 THEN 'medium'
                            ELSE 'low'
                        END as red_level,
                        CASE 
                            WHEN (metadata->>'yellow')::float > 60 THEN 'high'
                            WHEN (metadata->>'yellow')::float > 30 THEN 'medium'
                            ELSE 'low'
                        END as yellow_level,
                        CASE 
                            WHEN (metadata->>'blue')::float > 60 THEN 'high'
                            WHEN (metadata->>'blue')::float > 30 THEN 'medium'
                            ELSE 'low'
                        END as blue_level,
                        status
                    FROM experiments
                    WHERE created_at > NOW() - {interval}
                )
                SELECT 
                    red_level, yellow_level, blue_level,
                    COUNT(*) as total_combinations,
                    COUNT(*) FILTER (WHERE status = 'completed') as successful_combinations
                FROM color_ranges
                GROUP BY red_level, yellow_level, blue_level
                ORDER BY total_combinations DESC
            """)

            return {
                "success_trend": [dict(row) for row in success_trend],
                "error_patterns": [dict(row) for row in error_patterns],
                "color_statistics": [dict(row) for row in color_stats]
            }

    async def log_user_activity(self, user_id: str, action: str, details: Dict[str, Any] = None) -> str:
        """Log user activity
        
        Args:
            user_id: User ID
            action: Activity type (e.g., 'login', 'experiment_start', 'view_results')
            details: Additional activity details
        """
        async with self.postgres_pool.acquire() as conn:
            activity_id = await conn.fetchval("""
                INSERT INTO user_activity_log (
                    user_id,
                    action,
                    details,
                    ip_address,
                    created_at
                ) VALUES ($1, $2, $3, $4, NOW())
                RETURNING id
            """, user_id, action, json.dumps(details) if details else None, details.get('ip_address') if details else None)

            # If it's a security-sensitive action, also log to MongoDB for detailed analysis
            if action in ['login', 'login_failed', 'password_change', 'permission_change']:
                await self.mongodb_client.security_logs.insert_one({
                    "postgres_id": str(activity_id),
                    "user_id": user_id,
                    "action": action,
                    "details": details,
                    "created_at": datetime.utcnow()
                })

            return str(activity_id)

    async def get_user_activity_history(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get user activity history
        
        Args:
            user_id: User ID
            limit: Maximum number of records to return
        """
        async with self.postgres_pool.acquire() as conn:
            activities = await conn.fetch("""
                SELECT 
                    al.id,
                    al.action,
                    al.details,
                    al.ip_address,
                    al.created_at,
                    u.email
                FROM user_activity_log al
                JOIN users u ON al.user_id = u.id
                WHERE al.user_id = $1
                ORDER BY al.created_at DESC
                LIMIT $2
            """, user_id, limit)
            
            return [dict(activity) for activity in activities]

    async def get_security_audit_log(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get security audit log for a specific time period"""
        async with self.postgres_pool.acquire() as conn:
            audit_logs = await conn.fetch("""
                SELECT 
                    al.id,
                    al.action,
                    al.details,
                    al.ip_address,
                    al.created_at,
                    u.email,
                    u.role
                FROM user_activity_log al
                JOIN users u ON al.user_id = u.id
                WHERE al.action IN (
                    'login', 'login_failed', 'password_change', 
                    'permission_change', 'experiment_delete', 'user_disable'
                )
                AND al.created_at BETWEEN $1 AND $2
                ORDER BY al.created_at DESC
            """, start_date, end_date)
            
            return [dict(log) for log in audit_logs]

    # Plate Type Operations
    async def create_plate_type(self, plate_type: PlateType) -> UUID:
        """Create a new plate type."""
        async with self.postgres_pool.acquire() as conn:
            plate_type_id = await conn.fetchval("""
                INSERT INTO structured.plate_types (name, wells_count, description, metadata)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            """, plate_type.name, plate_type.wells_count, plate_type.description, plate_type.metadata)
            return plate_type_id

    async def get_plate_type(self, plate_type_id: UUID) -> Optional[PlateType]:
        """Get plate type by ID."""
        async with self.postgres_pool.acquire() as conn:
            record = await conn.fetchrow("""
                SELECT * FROM structured.plate_types WHERE id = $1
            """, plate_type_id)
            return PlateType(**dict(record)) if record else None

    # Enhanced Experiment Operations
    @task(retries=3)
    async def create_experiment(self, experiment: Experiment) -> str:
        """Create a new experiment with dual-write pattern."""
        async with self.postgres_pool.acquire() as conn:
            async with conn.transaction():
                # Check user quota
                remaining_quota = await conn.fetchval("""
                    SELECT quota_remaining
                    FROM structured.users
                    WHERE id = $1
                    FOR UPDATE
                """, experiment.user_id)
                
                if remaining_quota <= 0:
                    raise ValueError("User has no remaining experiment quota")
                
                # Decrement quota
                await conn.execute("""
                    UPDATE structured.users
                    SET quota_remaining = quota_remaining - 1
                    WHERE id = $1
                """, experiment.user_id)
                
                # Insert experiment
                experiment_id = await conn.fetchval("""
                    INSERT INTO semi_structured.experiments 
                    (user_id, plate_type_id, status, raw_data_s3_path, metadata, protocol_data)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id
                """, experiment.user_id, experiment.plate_type_id, experiment.status,
                experiment.raw_data_s3_path, experiment.metadata, experiment.protocol_data)

                try:
                    # Insert into MongoDB
                    mongo_result = await self.mongodb_client.experiments.insert_one({
                        "postgres_id": str(experiment_id),
                        "user_id": str(experiment.user_id),
                        "plate_type_id": str(experiment.plate_type_id),
                        "status": experiment.status,
                        "metadata": experiment.metadata,
                        "created_at": datetime.utcnow()
                    })

                    # Update PostgreSQL with MongoDB reference
                    await conn.execute("""
                        UPDATE semi_structured.experiments 
                        SET mongo_id = $1 
                        WHERE id = $2
                    """, str(mongo_result.inserted_id), experiment_id)

                except Exception as e:
                    self.logger.error(f"MongoDB write failed: {e}")
                    raise

                return str(experiment_id)

    async def get_experiment_with_details(self, experiment_id: UUID) -> Optional[ExperimentWithDetails]:
        """Get experiment with all related details."""
        async with self.postgres_pool.acquire() as conn:
            experiment = await conn.fetchrow("""
                SELECT e.*, pt.*
                FROM semi_structured.experiments e
                JOIN structured.plate_types pt ON e.plate_type_id = pt.id
                WHERE e.id = $1
            """, experiment_id)
            
            if not experiment:
                return None

            wells = await conn.fetch("""
                SELECT * FROM semi_structured.wells
                WHERE experiment_id = $1
            """, experiment_id)

            ml_analysis = await conn.fetchrow("""
                SELECT * FROM semi_structured.ml_analysis
                WHERE experiment_id = $1
                ORDER BY created_at DESC
                LIMIT 1
            """, experiment_id)

            return ExperimentWithDetails(
                **dict(experiment),
                plate_type=PlateType(**dict(experiment)),
                wells=[Well(**dict(w)) for w in wells],
                ml_analysis=MLAnalysis(**dict(ml_analysis)) if ml_analysis else None
            )

    # ML Analysis Operations
    async def create_ml_analysis(self, analysis: MLAnalysis) -> UUID:
        """Create a new ML analysis record."""
        async with self.postgres_pool.acquire() as conn:
            analysis_id = await conn.fetchval("""
                INSERT INTO semi_structured.ml_analysis 
                (experiment_id, model_version, input_data, output_data, confidence_scores)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """, analysis.experiment_id, analysis.model_version,
            analysis.input_data, analysis.output_data, analysis.confidence_scores)
            return analysis_id

    async def update_ml_analysis_review(
        self, 
        analysis_id: UUID, 
        review_status: ReviewStatus,
        reviewed_by: UUID
    ) -> bool:
        """Update ML analysis review status."""
        async with self.postgres_pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE semi_structured.ml_analysis
                SET review_status = $1, reviewed_by = $2, reviewed_at = CURRENT_TIMESTAMP
                WHERE id = $3
            """, review_status, reviewed_by, analysis_id)
            return result == "UPDATE 1"

    # Audit Logging
    async def log_audit_event(self, audit: AuditLog) -> UUID:
        """Log an audit event."""
        async with self.postgres_pool.acquire() as conn:
            audit_id = await conn.fetchval("""
                INSERT INTO structured.audit_log 
                (table_name, record_id, action, old_data, new_data, user_id)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """, audit.table_name, audit.record_id, audit.action,
            audit.old_data, audit.new_data, audit.user_id)
            return audit_id 
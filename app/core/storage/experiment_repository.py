from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from uuid import UUID
import asyncpg
import motor.motor_asyncio
from prefect import task

from .models import (
    Experiment, Well, MLAnalysis,
    ExperimentStatus, DataVersion,
    DataTransformation, ETLJob
)

logger = logging.getLogger(__name__)

class ExperimentRepository:
    """Repository for managing experiment data with dual-write capability."""
    
    def __init__(self, postgres_pool: asyncpg.Pool, mongodb_client: motor.motor_asyncio.AsyncIOMotorClient):
        """Initialize repository with database connections."""
        self.postgres_pool = postgres_pool
        self.mongodb_client = mongodb_client
        self.mongodb = mongodb_client.get_database("ot2db")
    
    @task(retries=3, retry_delay_seconds=1)
    async def save_experiment_result(self, experiment_data: Dict[str, Any]) -> str:
        """Save experiment result using dual-write pattern.
        
        Args:
            experiment_data: Experiment data to save
            
        Returns:
            str: Experiment ID
        """
        try:
            # Start PostgreSQL transaction
            async with self.postgres_pool.acquire() as conn:
                async with conn.transaction():
                    # Insert into PostgreSQL
                    experiment_id = await conn.fetchval("""
                        INSERT INTO experiments (
                            user_id, plate_type_id, status, metadata,
                            protocol_data, results_data, created_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                        RETURNING id
                    """, 
                    experiment_data["user_id"],
                    experiment_data["plate_type_id"],
                    ExperimentStatus.COMPLETED.value,
                    experiment_data["metadata"],
                    experiment_data["protocol_data"],
                    experiment_data["results_data"],
                    datetime.now()
                    )
                    
                    # Insert wells data
                    for well in experiment_data.get("wells", []):
                        await conn.execute("""
                            INSERT INTO wells (
                                experiment_id, well_id, status,
                                metadata, measurement_data, analysis_results
                            ) VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        experiment_id,
                        well["well_id"],
                        well["status"],
                        well["metadata"],
                        well["measurement_data"],
                        well["analysis_results"]
                        )
            
            # Write to MongoDB
            mongo_result = await self.mongodb.experiments.insert_one({
                "postgres_id": str(experiment_id),
                "raw_data": experiment_data.get("raw_data"),
                "spectral_data": experiment_data.get("spectral_data"),
                "created_at": datetime.now()
            })
            
            logger.info(f"Saved experiment {experiment_id} with MongoDB ID {mongo_result.inserted_id}")
            return str(experiment_id)
            
        except Exception as e:
            logger.error(f"Failed to save experiment: {str(e)}")
            raise
    
    async def get_experiment_history(self, 
                                   user_id: UUID,
                                   start_date: Optional[datetime] = None,
                                   end_date: Optional[datetime] = None,
                                   status: Optional[ExperimentStatus] = None) -> List[Dict[str, Any]]:
        """Get experiment history with filters.
        
        Args:
            user_id: User ID to filter by
            start_date: Optional start date filter
            end_date: Optional end date filter
            status: Optional status filter
            
        Returns:
            List of experiment records
        """
        try:
            query = """
                SELECT e.*, array_agg(w.*) as wells
                FROM experiments e
                LEFT JOIN wells w ON e.id = w.experiment_id
                WHERE e.user_id = $1
            """
            params = [user_id]
            
            if start_date:
                query += " AND e.created_at >= $" + str(len(params) + 1)
                params.append(start_date)
                
            if end_date:
                query += " AND e.created_at <= $" + str(len(params) + 1)
                params.append(end_date)
                
            if status:
                query += " AND e.status = $" + str(len(params) + 1)
                params.append(status.value)
                
            query += " GROUP BY e.id ORDER BY e.created_at DESC"
            
            async with self.postgres_pool.acquire() as conn:
                records = await conn.fetch(query, *params)
                
            # Enrich with MongoDB data
            results = []
            for record in records:
                # Get MongoDB data
                mongo_data = await self.mongodb.experiments.find_one({
                    "postgres_id": str(record["id"])
                })
                
                # Combine data
                experiment_data = dict(record)
                if mongo_data:
                    experiment_data["raw_data"] = mongo_data.get("raw_data")
                    experiment_data["spectral_data"] = mongo_data.get("spectral_data")
                
                results.append(experiment_data)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get experiment history: {str(e)}")
            raise
    
    async def verify_data_consistency(self, experiment_id: UUID) -> bool:
        """Verify data consistency between PostgreSQL and MongoDB.
        
        Args:
            experiment_id: Experiment ID to verify
            
        Returns:
            bool: True if data is consistent
        """
        try:
            # Get PostgreSQL data
            async with self.postgres_pool.acquire() as conn:
                pg_record = await conn.fetchrow(
                    "SELECT * FROM experiments WHERE id = $1",
                    experiment_id
                )
                
            if not pg_record:
                return False
                
            # Get MongoDB data
            mongo_record = await self.mongodb.experiments.find_one({
                "postgres_id": str(experiment_id)
            })
            
            if not mongo_record:
                return False
                
            # Compare critical fields
            return (
                pg_record["created_at"] == mongo_record["created_at"] and
                str(pg_record["id"]) == mongo_record["postgres_id"]
            )
            
        except Exception as e:
            logger.error(f"Failed to verify data consistency: {str(e)}")
            return False
    
    async def repair_inconsistency(self, experiment_id: UUID) -> bool:
        """Repair data inconsistency between databases.
        
        Args:
            experiment_id: Experiment ID to repair
            
        Returns:
            bool: True if repair successful
        """
        try:
            # Get PostgreSQL data
            async with self.postgres_pool.acquire() as conn:
                pg_record = await conn.fetchrow(
                    "SELECT * FROM experiments WHERE id = $1",
                    experiment_id
                )
                
            if not pg_record:
                return False
                
            # Update or insert MongoDB record
            await self.mongodb.experiments.update_one(
                {"postgres_id": str(experiment_id)},
                {"$set": {
                    "postgres_id": str(experiment_id),
                    "created_at": pg_record["created_at"]
                }},
                upsert=True
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to repair inconsistency: {str(e)}")
            return False

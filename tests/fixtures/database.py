import pytest
import asyncio
from typing import AsyncGenerator, Dict
import asyncpg
import motor.motor_asyncio
from datetime import datetime
from app.core.storage.db_manager import DatabaseManager
from app.core.auth.auth_manager import UserRole

TEST_POSTGRES_DSN = "postgresql://test_user:test_password@localhost:5432/test_db"
TEST_MONGODB_URI = "mongodb://localhost:27017/test_db"

@pytest.fixture
async def test_db_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """Create a test database pool"""
    pool = await asyncpg.create_pool(
        TEST_POSTGRES_DSN,
        min_size=2,
        max_size=5
    )
    
    async with pool.acquire() as conn:
        # Load test schema
        with open("app/core/storage/migrations/V1__initial_schema.sql") as f:
            await conn.execute(f.read())
        with open("app/core/storage/migrations/V2__add_activity_logging.sql") as f:
            await conn.execute(f.read())
    
    yield pool
    await pool.close()

@pytest.fixture
async def test_mongodb() -> AsyncGenerator[motor.motor_asyncio.AsyncIOMotorClient, None]:
    """Create a test MongoDB client"""
    client = motor.motor_asyncio.AsyncIOMotorClient(TEST_MONGODB_URI)
    yield client
    await client.drop_database("test_db")
    client.close()

@pytest.fixture
async def db_manager(test_db_pool, test_mongodb) -> DatabaseManager:
    """Create a test database manager"""
    manager = DatabaseManager(TEST_POSTGRES_DSN, TEST_MONGODB_URI)
    manager.postgres_pool = test_db_pool
    manager.mongodb_client = test_mongodb
    return manager

@pytest.fixture
async def test_user(db_manager) -> Dict:
    """Create a test user"""
    async with db_manager.postgres_pool.acquire() as conn:
        user = await conn.fetchrow("""
            INSERT INTO users (email, role, hashed_password, quota_remaining)
            VALUES ($1, $2, $3, $4)
            RETURNING id, email, role
        """, "test@example.com", UserRole.RESEARCHER.value, "hashed_password", 10)
        
        return dict(user)

@pytest.fixture
async def test_experiment(db_manager, test_user) -> Dict:
    """Create a test experiment"""
    metadata = {
        "red": 30,
        "yellow": 40,
        "blue": 30
    }
    
    experiment_id = await db_manager.dual_write_experiment(
        test_user["id"],
        metadata
    )
    
    async with db_manager.postgres_pool.acquire() as conn:
        experiment = await conn.fetchrow("""
            SELECT * FROM experiments WHERE id = $1
        """, experiment_id)
        
        return dict(experiment)

@pytest.fixture
async def test_well(db_manager, test_experiment) -> Dict:
    """Create a test well"""
    async with db_manager.postgres_pool.acquire() as conn:
        well = await conn.fetchrow("""
            INSERT INTO wells (well_id, experiment_id, status, metadata)
            VALUES ($1, $2, $3, $4)
            RETURNING *
        """, "A1", test_experiment["id"], "available", {"temperature": 25})
        
        return dict(well) 
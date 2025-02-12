"""Database initialization script."""
import asyncio
import asyncpg
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_db_and_user():
    """Create database and user if they don't exist."""
    try:
        # Connect to default database as postgres user
        system_conn = await asyncpg.connect(
            user="postgres",
            password="test_password",
            database="postgres",
            host="localhost",
            port=5432
        )
        
        # Create user if not exists
        try:
            await system_conn.execute("""
                DO $$ 
                BEGIN
                    CREATE USER test_user WITH PASSWORD 'test_password';
                    EXCEPTION WHEN DUPLICATE_OBJECT THEN
                    RAISE NOTICE 'User already exists';
                END
                $$;
            """)
            logger.info("Created user 'test_user'")
        except Exception as e:
            logger.warning(f"User creation warning: {str(e)}")
        
        # Create database if not exists
        try:
            await system_conn.execute("""
                CREATE DATABASE test_db
                    WITH 
                    OWNER = test_user
                    ENCODING = 'UTF8'
                    LC_COLLATE = 'en_US.UTF-8'
                    LC_CTYPE = 'en_US.UTF-8'
                    TEMPLATE = template0;
            """)
            logger.info("Created database 'test_db'")
        except Exception as e:
            logger.warning(f"Database creation warning: {str(e)}")
        
        # Grant privileges
        await system_conn.execute("""
            GRANT ALL PRIVILEGES ON DATABASE test_db TO test_user;
        """)
        
        await system_conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to create database and user: {str(e)}")
        return False

async def clean_database(conn):
    """Remove existing schemas and tables."""
    try:
        # Drop existing schemas if they exist
        await conn.execute("""
            DROP SCHEMA IF EXISTS structured CASCADE;
            DROP SCHEMA IF EXISTS semi_structured CASCADE;
        """)
        logger.info("Cleaned existing schemas")
        return True
    except Exception as e:
        logger.error(f"Failed to clean database: {str(e)}")
        return False

async def init_db():
    """Initialize database with schema and initial data."""
    try:
        # First create database and user
        if not await create_db_and_user():
            raise Exception("Failed to create database and user")
        
        # Database connection parameters
        db_params = {
            "user": "test_user",
            "password": "test_password",
            "database": "test_db",
            "host": "localhost",
            "port": 5432
        }
        
        # Connect to database
        conn = await asyncpg.connect(**db_params)
        logger.info("Connected to database")
        
        # Clean existing database objects
        if not await clean_database(conn):
            raise Exception("Failed to clean database")
        
        # Read and execute schema files
        migrations_dir = Path("app/core/storage/migrations")
        for migration_file in sorted(migrations_dir.glob("V*__*.sql")):
            logger.info(f"Applying migration: {migration_file.name}")
            with open(migration_file) as f:
                sql = f.read()
                await conn.execute(sql)
        
        # Insert test data
        logger.info("Inserting test data...")
        
        # Insert test plate type
        plate_type_id = await conn.fetchval("""
            INSERT INTO structured.plate_types (name, wells_count, description)
            VALUES ('96-well-plate', 96, 'Standard 96 well plate')
            RETURNING id
        """)
        
        # Insert test user
        user_id = await conn.fetchval("""
            INSERT INTO structured.users (email, role, hashed_password)
            VALUES ('test@example.com', 'researcher', 'test_password_hash')
            RETURNING id
        """)
        
        logger.info("Database initialization completed successfully")
        await conn.close()
        
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(init_db()) 
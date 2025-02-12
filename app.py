import asyncio
import os
import logging
from app.ui.gradio_app import EnhancedGradioUI
from app.core.auth.auth_manager import AuthManager
from app.core.storage.db_manager import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def init_database(db_manager: DatabaseManager) -> bool:
    """Initialize database connections and verify they are working."""
    try:
        await db_manager.connect()
        logger.info("Database connections established successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database connections: {str(e)}")
        return False

async def main():
    try:
        # Get environment variables with defaults
        jwt_secret = os.getenv("JWT_SECRET_KEY", "dev_secret_key")
        postgres_user = os.getenv("POSTGRES_USER", "test_user")
        postgres_password = os.getenv("POSTGRES_PASSWORD", "test_password")
        postgres_db = os.getenv("POSTGRES_DB", "test_db")
        postgres_host = os.getenv("POSTGRES_HOST", "localhost")
        mongodb_host = os.getenv("MONGODB_HOST", "localhost")
        
        # Initialize managers
        logger.info("Initializing authentication manager...")
        auth_manager = AuthManager(
            secret_key=jwt_secret,
            algorithm="HS256"
        )
        
        # Construct database connection strings
        postgres_dsn = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:5432/{postgres_db}"
        mongodb_uri = f"mongodb://{mongodb_host}:27017/test_db"
        
        logger.info("Initializing database manager...")
        db_manager = DatabaseManager(
            postgres_dsn=postgres_dsn,
            mongodb_uri=mongodb_uri
        )
        
        # Initialize database connections
        if not await init_database(db_manager):
            logger.error("Failed to initialize databases. Exiting...")
            return
        
        # Create UI
        logger.info("Creating Gradio interface...")
        ui = EnhancedGradioUI(auth_manager, db_manager)
        app = ui.create_interface()
        
        # Launch the interface
        logger.info("Launching Gradio interface...")
        app.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=True
        )
        
    except Exception as e:
        logger.error(f"Application startup failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
import pytest
from datetime import datetime, timedelta
from app.core.auth.auth_manager import UserRole
from app.core.storage.db_manager import DatabaseManager

pytestmark = pytest.mark.asyncio

async def test_get_user_by_email(db_manager, test_user):
    """Test getting user by email"""
    user = await db_manager.get_user_by_email("test@example.com")
    assert user is not None
    assert user.email == "test@example.com"
    assert user.role == UserRole.RESEARCHER

async def test_get_user_experiments(db_manager, test_user, test_experiment):
    """Test getting user experiments"""
    experiments = await db_manager.get_user_experiments(test_user["email"])
    assert len(experiments) > 0
    assert experiments[0]["id"] == test_experiment["id"]

async def test_get_system_metrics(db_manager, test_experiment):
    """Test getting system metrics"""
    metrics = await db_manager.get_system_metrics()
    assert "active_experiments" in metrics
    assert "success_rate" in metrics
    assert "avg_duration" in metrics

async def test_experiment_statistics(db_manager, test_experiment):
    """Test getting experiment statistics"""
    stats = await db_manager.get_experiment_statistics("24h")
    assert "success_trend" in stats
    assert "error_patterns" in stats
    assert "color_statistics" in stats

async def test_user_activity_logging(db_manager, test_user):
    """Test user activity logging"""
    # Log some activities
    activity_id = await db_manager.log_user_activity(
        test_user["id"],
        "login",
        {"ip_address": "127.0.0.1"}
    )
    
    # Get activity history
    activities = await db_manager.get_user_activity_history(test_user["id"])
    assert len(activities) > 0
    assert activities[0]["action"] == "login"

async def test_dual_write_experiment(db_manager, test_user):
    """Test dual write for experiments"""
    metadata = {
        "red": 50,
        "yellow": 30,
        "blue": 20
    }
    
    # Create experiment
    experiment_id = await db_manager.dual_write_experiment(
        test_user["id"],
        metadata
    )
    
    # Verify in PostgreSQL
    async with db_manager.postgres_pool.acquire() as conn:
        pg_record = await conn.fetchrow(
            "SELECT * FROM experiments WHERE id = $1",
            experiment_id
        )
        assert pg_record is not None
    
    # Verify in MongoDB
    mongo_record = await db_manager.mongodb_client.experiments.find_one({
        "postgres_id": str(experiment_id)
    })
    assert mongo_record is not None

async def test_data_consistency(db_manager, test_experiment):
    """Test data consistency check"""
    is_consistent = await db_manager.verify_consistency(
        "experiments",
        test_experiment["id"]
    )
    assert is_consistent is True

async def test_quota_management(db_manager, test_user):
    """Test user quota management"""
    # Use up all quota
    metadata = {"red": 30, "yellow": 30, "blue": 30}
    for _ in range(10):  # Initial quota is 10
        await db_manager.dual_write_experiment(test_user["id"], metadata)
    
    # Try to create one more experiment
    with pytest.raises(ValueError, match="User has no remaining experiment quota"):
        await db_manager.dual_write_experiment(test_user["id"], metadata)

async def test_security_audit_log(db_manager, test_user):
    """Test security audit logging"""
    # Create some security events
    await db_manager.log_user_activity(
        test_user["id"],
        "login_failed",
        {"ip_address": "127.0.0.1", "reason": "invalid_password"}
    )
    
    # Get audit log
    start_date = datetime.utcnow() - timedelta(hours=1)
    end_date = datetime.utcnow() + timedelta(hours=1)
    audit_logs = await db_manager.get_security_audit_log(start_date, end_date)
    
    assert len(audit_logs) > 0
    assert audit_logs[0]["action"] == "login_failed" 
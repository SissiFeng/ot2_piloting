# OT-2 LCM System Deployment Guide

## Prerequisites
- Docker and Docker Compose installed
- Git installed
- Access to the project repository
- Basic understanding of terminal/command line
- Required access credentials:
  - PostgreSQL credentials
  - MongoDB credentials
  - JWT secret key
  - MQTT credentials (if using external broker)

## Step 1: Environment Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/OT-2-LCM.git
cd OT-2-LCM
```

2. Create environment file:
```bash
cp docker/.env.template docker/.env
```

3. Edit the `.env` file with your credentials:
```env
# Database Credentials
MONGODB_PASSWORD=your_mongodb_password
POSTGRES_PASSWORD=your_postgres_password

# Security
JWT_SECRET_KEY=your_jwt_secret_key

# MQTT Configuration (if needed)
MQTT_BROKER=your_mqtt_broker
MQTT_PORT=8883
MQTT_USERNAME=your_mqtt_username
MQTT_PASSWORD=your_mqtt_password
```

## Step 2: Database Initialization

1. Initialize the database schemas:
```bash
cd scripts
python init_db.py
```

This will:
- Create necessary database schemas
- Apply initial migrations
- Set up basic indexes

## Step 3: Docker Deployment

1. Build and start services:
```bash
cd docker
docker-compose build
docker-compose up -d
```

2. Verify services are running:
```bash
docker-compose ps
```

Expected output:
```
Name                 Command               State           Ports
-------------------------------------------------------------------------
ot2-app             /app/entrypoint.sh           Up      0.0.0.0:7860->7860/tcp
ot2-mongodb         docker-entrypoint.sh mongod   Up      27017/tcp
ot2-postgres        docker-entrypoint.sh postgres Up      5432/tcp
ot2-prometheus      /bin/prometheus ...          Up      9090/tcp
ot2-grafana         /run.sh                      Up      3000/tcp
```

## Step 4: Service Verification

1. Check web interface:
- Open browser and navigate to `http://localhost:7860`
- Verify Gradio interface loads correctly

2. Check monitoring:
- Grafana: `http://localhost:3000`
  - Default credentials: admin/admin
- Prometheus: `http://localhost:9090`

3. Verify database connections:
```bash
# Test PostgreSQL connection
docker-compose exec postgres psql -U test_user -d test_db -c "\dt"

# Test MongoDB connection
docker-compose exec mongodb mongosh --eval "db.adminCommand('ping')"
```

## Step 5: Initial Setup

1. Create first admin user:
```bash
python scripts/create_admin.py --email admin@example.com --password your_secure_password
```

2. Configure basic monitoring alerts in Grafana:
- Import provided dashboards
- Set up email notifications
- Configure basic alerts

## Step 6: Testing

1. Run basic system tests:
```bash
pytest tests/
```

2. Perform manual testing:
- Create test experiment
- Verify data collection
- Check data processing
- Validate monitoring

## Step 7: Backup Configuration

1. Set up automated backups:
```bash
# Configure backup schedule
docker-compose exec postgres pg_dump -U test_user test_db > backup.sql
```

2. Verify backup restoration:
```bash
# Test backup restoration
docker-compose exec postgres psql -U test_user test_db < backup.sql
```

## Monitoring and Maintenance

### Health Checks
Monitor these endpoints:
- Application: `http://localhost:7860/health`
- PostgreSQL: Check connection pool status
- MongoDB: Check replication status
- Prometheus: Check target status

### Key Metrics to Monitor
1. System Health:
   - CPU usage
   - Memory usage
   - Disk space
   - Network traffic

2. Application Metrics:
   - Request latency
   - Error rates
   - Active users
   - Experiment success rate

3. Database Metrics:
   - Connection pool status
   - Query performance
   - Storage usage
   - Backup status

## Troubleshooting

### Common Issues and Solutions

1. Service won't start:
```bash
# Check logs
docker-compose logs [service_name]

# Restart service
docker-compose restart [service_name]
```

2. Database connection issues:
```bash
# Check network
docker network ls
docker network inspect ot2-network

# Verify credentials
docker-compose exec postgres psql -U test_user -d test_db
```

3. Performance issues:
- Check Prometheus metrics
- Review Grafana dashboards
- Analyze application logs

### Emergency Procedures

1. Quick system restart:
```bash
docker-compose down
docker-compose up -d
```

2. Data recovery:
```bash
# Restore from latest backup
docker-compose exec postgres psql -U test_user test_db < latest_backup.sql
```

## Security Considerations

1. Change default passwords:
- Grafana admin password
- Database passwords
- Application admin password

2. Configure firewall rules:
```bash
# Example: Allow only necessary ports
sudo ufw allow 7860
sudo ufw allow 3000
```

3. Regular security updates:
```bash
# Update containers
docker-compose pull
docker-compose up -d
```

## Next Steps

After successful deployment:
1. Monitor system performance
2. Collect user feedback
3. Plan for:
   - SSO integration
   - External access implementation
   - Additional security measures

## Support

For issues or questions:
1. Check logs: `docker-compose logs`
2. Review documentation
3. Contact development team 
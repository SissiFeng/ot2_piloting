# OT-2 Liquid Color Mixing System

A system for controlling OT-2 liquid handling robot for color mixing experiments.

## Project Structure
```
.
├── app/                    # Application code
├── docker/                # Docker configuration
├── infrastructure/        # Cloud infrastructure code
│   ├── aws/              # AWS configurations
│   ├── azure/            # Azure configurations
│   └── gcp/              # GCP configurations
└── scripts/              # Utility scripts
```

## Environment Setup

### Environment Variables
The project uses environment variables for configuration. These are stored in `docker/.env` for local development.

1. Copy the environment template:
```bash
cp docker/.env.template docker/.env
```

2. Configure the following environment variables in your `.env` file:

#### Database Configuration
- `MONGODB_PASSWORD`: MongoDB database password
- `POSTGRES_USER`: PostgreSQL username
- `POSTGRES_PASSWORD`: PostgreSQL password
- `POSTGRES_DB`: PostgreSQL database name

#### Security
- `JWT_SECRET_KEY`: Secret key for JWT token generation (must be strong in production)

#### MQTT Configuration
- `MQTT_BROKER`: MQTT broker hostname
- `MQTT_PORT`: MQTT broker port (default: 8883)
- `MQTT_USERNAME`: MQTT username
- `MQTT_PASSWORD`: MQTT password

#### Monitoring
- `GRAFANA_PASSWORD`: Grafana admin password

#### Workflow
- `PREFECT_API_URL`: Prefect API URL (default: http://prefect:4200/api)

### Security Notes
- Never commit the `.env` file to version control
- Use strong passwords in production
- Rotate credentials regularly
- Use secrets management in production environments

## Quick Start with Docker

1. Set up environment variables as described above

2. Build and start services:
```bash
cd docker
docker-compose up --build
```

3. Access the services:
- Web UI: http://localhost:7860
- Grafana: http://localhost:3000
- Prefect UI: http://localhost:4200

## Development Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

2. Set up pre-commit hooks:
```bash
pre-commit install
```

3. Run the application:
```bash
python app.py
```

## Features
- Automated liquid color mixing
- Real-time experiment monitoring
- User quota management
- Secure authentication
- Multi-cloud deployment support
- Prefect workflow orchestration

## Documentation
Detailed documentation can be found in the /docs directory.

## Testing
Run tests with:
```bash
pytest
```

## Contributing
1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License
[Add your license information here]

## Deployment Guide

### Local Deployment
1. Clone the repository
2. Follow the "Environment Setup" section above
3. Use docker-compose for local deployment

### GitHub Actions Deployment
If you want to use GitHub Actions for automated deployment, follow these steps:

1. Fork this repository to your GitHub account

2. Set up the following Secrets in your repository (Settings -> Secrets and variables -> Actions):
   ```
   MONGODB_PASSWORD
   POSTGRES_USER
   POSTGRES_PASSWORD
   POSTGRES_DB
   JWT_SECRET_KEY
   MQTT_BROKER
   MQTT_USERNAME
   MQTT_PASSWORD
   GRAFANA_PASSWORD
   ```

3. Configure GitHub Container Registry:
   - Ensure GitHub Container Registry is enabled for your account
   - Generate a Personal Access Token (PAT) in your personal settings
   - Add the PAT to your repository Secrets as `GITHUB_TOKEN`

4. Customize Deployment:
   - Modify `.github/workflows/ci.yml` as needed
   - Adjust deployment targets and environment variables

### Manual Deployment
If you prefer not to use GitHub Actions, you can deploy manually:

1. Build Docker image:
   ```bash
   docker build -t ot2-lcm .
   ```

2. Create environment file:
   ```bash
   cp docker/.env.template docker/.env
   # Edit .env file with your configuration
   ```

3. Run services:
   ```bash
   docker-compose up -d
   ```

### Production Deployment Notes
For production deployments, consider the following:

1. Security Considerations:
   - Use strong passwords and keys
   - Rotate credentials regularly
   - Restrict network access
   - Enable audit logging

2. Environment Variables Management:
   - Use professional secrets management services in production
   - Recommended options:
     * AWS Secrets Manager
     * Azure Key Vault
     * HashiCorp Vault
     * GCP Secret Manager

3. Monitoring and Logging:
   - Set up appropriate monitoring alerts
   - Configure log aggregation
   - Regular security updates check

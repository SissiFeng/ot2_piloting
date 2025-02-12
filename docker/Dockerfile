# Build stage
FROM python:3.9-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Add additional dependencies for new features
RUN pip install --no-cache-dir \
    psycopg2-binary \
    fastapi \
    uvicorn \
    python-jose[cryptography] \
    passlib[bcrypt] \
    python-multipart \
    prefect>=2.0.0

# Final stage
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.9/site-packages/ /usr/local/lib/python3.9/site-packages/

# Copy application code
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    MONGODB_PASSWORD="" \
    POSTGRES_PASSWORD="" \
    MQTT_BROKER="" \
    MQTT_PORT=8883 \
    MQTT_USERNAME="" \
    MQTT_PASSWORD="" \
    JWT_SECRET_KEY="" \
    PREFECT_API_URL=""

# Expose port
EXPOSE 7860

# Create entrypoint script
RUN echo '#!/bin/bash\n\
if [ "$DEPLOYMENT_TYPE" = "api" ]; then\n\
    uvicorn api.main:app --host 0.0.0.0 --port 7860\n\
else\n\
    python app.py\n\
fi' > /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"] 
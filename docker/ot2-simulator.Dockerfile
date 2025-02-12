FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements-simulator.txt .
RUN pip install --no-cache-dir -r requirements-simulator.txt

# Copy simulator code
COPY simulator/ot2_simulator.py .

CMD ["python", "ot2_simulator.py"]

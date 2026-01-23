FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (but NOT models - too large)
COPY app/ ./app/
COPY scripts/ ./scripts/

# Create directories for data and models
RUN mkdir -p data/uploads data/heatmaps data/reverse-images data/contributions models/

# Expose port (Railway will set $PORT)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl --fail http://localhost:8000/health || exit 1

# Start command (Railway will override with $PORT)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

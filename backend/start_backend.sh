#!/bin/bash
# Stop any running backend
pkill -f "uvicorn app.main:app" 2>/dev/null
sleep 2

# Change to backend directory
cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Set environment variables
export USE_CELERY=false
export DATABASE_URL="sqlite:///./deepfake.db"

# Start the server in foreground (you'll see all logs)
echo "=========================================="
echo "Starting DeepVerify Backend Server"
echo "=========================================="
echo "Server will run on http://localhost:8000"
echo "Press Ctrl+C to stop"
echo "=========================================="
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > backend.log 2>&1 &


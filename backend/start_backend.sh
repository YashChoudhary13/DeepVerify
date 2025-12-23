#!/bin/bash

# Configuration
VENV_DIR="venv"
PYTHON_CMD="python3"
PORT=8000
HOST="0.0.0.0"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}   Starting DeepVerify Backend Server     ${NC}"
echo -e "${GREEN}==========================================${NC}"

# 1. Change to directory of this script
cd "$(dirname "$0")" || exit 1

# 2. Check/Create Virtual Environment
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}[INFO] Creating virtual environment...${NC}"
    $PYTHON_CMD -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo -e "${RED}[ERROR] Failed to create virtual environment.{NC}"
        exit 1
    fi
fi

# 3. Activate Virtual Environment
source "$VENV_DIR/bin/activate"

# 4. Install Dependencies
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}[INFO] Checking dependencies...${NC}"
    pip install -r requirements.txt > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo -e "${RED}[WARN] Failed to install some dependencies. Trying to continue...${NC}"
    else
        echo -e "${GREEN}[OK] Dependencies installed.${NC}"
    fi
else
    echo -e "${RED}[ERROR] requirements.txt not found!${NC}"
    exit 1
fi

# 5. Stop any existing backend process (Robust kill)
PID=$(lsof -ti:$PORT)
if [ -n "$PID" ]; then
    echo -e "${YELLOW}[INFO] Stopping process on port $PORT (PID: $PID)...${NC}"
    kill -9 $PID 2>/dev/null
    sleep 1
fi

pkill -f "uvicorn app.main:app" 2>/dev/null

# 6. Set Environment Variables
export USE_CELERY=false
export DATABASE_URL="sqlite:///./deepfake.db"

# 7. Start Server
echo -e "${GREEN}[INFO] Starting Uvicorn on http://$HOST:$PORT${NC}"
echo -e "${YELLOW}Logs are being written to backend.log${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop (if verify script is not running)${NC}"

# Clear old log
> backend.log

# Run in background to not block shell if called from another script, 
# OR run in foreground if user wants to see output? 
# Current usage seems to prefer background with log redirection.
nohup uvicorn app.main:app --host $HOST --port $PORT --reload > backend.log 2>&1 &
SERVER_PID=$!

echo -e "${GREEN}[OK] Server started with PID $SERVER_PID${NC}"

# Optional: Wait a moment and check if it's still running
sleep 3
if ps -p $SERVER_PID > /dev/null; then
    echo -e "${GREEN}Backend is RUNNING!${NC}"
else
    echo -e "${RED}Backend failed to start. Check backend.log:${NC}"
    tail -n 10 backend.log
fi

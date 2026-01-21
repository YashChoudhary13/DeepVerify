@echo off
REM Windows startup script for DeepVerify Backend

echo Starting DeepVerify Backend...

REM Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Please create it first with: python -m venv venv
    echo Then install requirements: venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment and start server
call venv\Scripts\activate.bat
uvicorn app.main:app --reload --port 8000

pause

@echo off
setlocal
chcp 65001 > nul

:: Python virtual environment setup
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

:: Start application
echo Starting Desktop Agent...
echo Note: Cannot start if another instance is already running
python src/main.py

:: Display errors if any
if errorlevel 1 (
    echo An error occurred.
    pause
)

endlocal 
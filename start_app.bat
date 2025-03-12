@echo off
cd /d %~dp0
start /b cmd /c "cd MCP && python src/server.py"
timeout /t 3
python main.py
pause 
@echo off
cd /d "%~dp0backend"
call venv\Scripts\activate.bat
echo Backend: http://localhost:8000   API docs: http://localhost:8000/docs
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause

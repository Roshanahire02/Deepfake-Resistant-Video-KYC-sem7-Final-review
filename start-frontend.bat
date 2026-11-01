@echo off
cd /d "%~dp0frontend"
echo Frontend: http://localhost:5173
call npm run dev
pause

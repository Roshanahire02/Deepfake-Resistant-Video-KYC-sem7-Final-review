@echo off
setlocal
cd /d "%~dp0"
echo ===== KYC demo setup (first time only) =====

where python >nul 2>nul
if errorlevel 1 (
  echo Python not found. Install Python 3.10, 3.11 or 3.12 from python.org and tick "Add python.exe to PATH".
  pause
  exit /b 1
)
python -c "import sys; sys.exit(0 if (3,10)<=sys.version_info[:2]<=(3,12) else 1)"
if errorlevel 1 (
  echo Unsupported Python version. Please use Python 3.10, 3.11 or 3.12 - mediapipe has no wheels for others.
  pause
  exit /b 1
)
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js not found. Install Node 20.19+ or 22.12+ LTS from nodejs.org.
  pause
  exit /b 1
)
node -e "const [a,b]=process.versions.node.split('.').map(Number);process.exit((a===20&&b>=19)||(a===22&&b>=12)||a>=23?0:1)"
if errorlevel 1 (
  echo Node.js is too old. Install Node 20.19+ or 22.12+ LTS from nodejs.org.
  pause
  exit /b 1
)

cd backend
if not exist venv python -m venv venv
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements-lite.txt
if errorlevel 1 (
  echo Backend install failed - see README.md troubleshooting.
  pause
  exit /b 1
)
python -m app.scripts.setup_env
python -m app.scripts.seed_demo

cd ..\frontend
call npm install
if errorlevel 1 (
  echo Frontend install failed - see README.md troubleshooting.
  pause
  exit /b 1
)
echo.
echo ===== Setup complete. Now run start-backend.bat and start-frontend.bat (two windows) =====
pause

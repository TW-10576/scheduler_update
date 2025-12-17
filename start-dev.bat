@echo off

REM ###############################################################################
REM # Shift Scheduler - Development Startup Script (Windows)
REM #
REM # This script starts PostgreSQL in Docker only.
REM # Backend and Frontend must be started separately.
REM #
REM # Usage: start-dev.bat
REM ###############################################################################

setlocal enabledelayedexpansion

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ❌ Docker is not installed. Please install Docker Desktop for Windows first.
    echo.
    pause
    exit /b 1
)

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"

echo.
echo ════════════════════════════════════════════════════════════════
echo 🚀 Shift Scheduler - Development Environment (Windows)
echo ════════════════════════════════════════════════════════════════
echo.

echo 📦 Starting PostgreSQL database...
echo.

REM Navigate to project root
cd /d "%SCRIPT_DIR%"

REM Start PostgreSQL
docker compose up -d

REM Wait for PostgreSQL to be ready
echo.
echo ⏳ Waiting for PostgreSQL to be ready...
timeout /t 5 /nobreak

echo.
echo ════════════════════════════════════════════════════════════════
echo ✅ PostgreSQL Database Started Successfully!
echo ════════════════════════════════════════════════════════════════
echo.

echo Database Details:
echo    Host: localhost
echo    Port: 5432
echo    User: postgres
echo    Password: postgres123
echo    Database: shift_scheduler
echo.

echo Next Steps - Start Backend ^& Frontend:
echo.
echo Terminal 2 - Backend:
echo    cd "%SCRIPT_DIR%backend"
echo    pip install -r requirements.txt
echo    python run.py
echo.

echo Terminal 3 - Frontend:
echo    cd "%SCRIPT_DIR%frontend"
echo    npm install
echo    npm run dev
echo.

echo Access:
echo    Frontend: http://localhost:5173
echo    Backend: http://localhost:8000
echo    API Docs: http://localhost:8000/docs
echo.

echo Useful Commands:
echo    Stop Database: docker compose down
echo    View Logs: docker compose logs -f postgres
echo    Remove Data: docker compose down -v
echo.

echo ════════════════════════════════════════════════════════════════
echo ✅ Ready for development!
echo ════════════════════════════════════════════════════════════════
echo.

REM Show logs
echo PostgreSQL logs (close window to exit):
docker compose logs -f postgres

endlocal

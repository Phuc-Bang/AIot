@echo off
echo ===================================================
echo   Lab 6 Enhanced: Docker Launcher
echo ===================================================
echo.
echo Executing: docker compose up --build -d
echo.
docker compose up --build -d
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to launch Docker container. Please check if Docker Desktop is running.
    pause
    exit /b %errorlevel%
)
echo.
echo ===================================================
echo   Dashboard is ready at: http://localhost:8001/
echo ===================================================
echo.
pause

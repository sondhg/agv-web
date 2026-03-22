@echo off
REM ============================================================
REM  AGV Simulation Runner
REM  Usage:
REM    run_simulation.bat                   - Run basic scenario
REM    run_simulation.bat burst             - Run burst scenario
REM    run_simulation.bat all               - Run all scenarios
REM    run_simulation.bat list              - List scenarios
REM    run_simulation.bat basic --agvs 5    - Custom fleet size
REM ============================================================

cd /d "%~dp0"

echo.
echo ============================================================
echo   AGV Simulation System - VDA5050
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Install dependencies if needed
pip show paho-mqtt >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install paho-mqtt requests
)

REM Handle arguments
if "%~1"=="" (
    echo Running: basic scenario
    python multi_agent_runner.py --scenario basic
) else if "%~1"=="list" (
    python multi_agent_runner.py --list
) else if "%~1"=="all" (
    echo Running: ALL scenarios
    python multi_agent_runner.py --scenario all
) else (
    echo Running: %* scenario
    python multi_agent_runner.py --scenario %*
)

echo.
echo Simulation complete. Results saved in results/ directory.
echo.
pause

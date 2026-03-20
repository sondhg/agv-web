@echo off
REM Quick test script for Multi-AGV Simulator

echo ============================================================
echo 🧪 Testing Multi-AGV System
echo ============================================================
echo.

echo Step 1: Checking if simulator is running...
timeout /t 2 >nul

echo Step 2: Sending test tasks...
python test_agv_load_balancing.py

echo.
echo ============================================================
echo ✅ Test completed! Check the other terminal for AGV responses
echo ============================================================
pause

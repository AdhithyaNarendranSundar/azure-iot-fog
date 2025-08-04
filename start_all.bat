@echo off
title IoT Weather Dashboard Launcher
echo Starting virtual environment...
call .venv\Scripts\activate.bat

echo Launching multi-device simulator...
start cmd /k python multi_device_simulator.py

timeout /t 2

echo Starting IoT Hub listener...
start cmd /k python iot_hub_listener_multi.py

timeout /t 2

echo Starting Streamlit dashboard...
start cmd /k streamlit run newdashboard.py

echo All services started.
pause

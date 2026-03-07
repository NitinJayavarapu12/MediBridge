@echo off
echo Starting MediBridge...
call venv\Scripts\activate
start http://localhost:8000
python main.py
pause
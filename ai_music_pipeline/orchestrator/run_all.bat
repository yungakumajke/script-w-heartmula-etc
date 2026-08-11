@echo off
setlocal
cd /d %~dp0

if not exist ".venv\Scripts\activate.bat" (
    echo [1/4] Creating Python venv...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo [2/4] Upgrading pip and installing requirements...
pip install -r requirements.txt

echo [3/4] Starting pipeline service...
start "AI Music Pipeline" cmd /k python pipeline_service.py

timeout /t 3 >nul

echo [4/4] Sending test generation request...
curl.exe -X POST http://127.0.0.1:5055/generate ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"demo_001\",\"tags\":\"cinematic,modern,epic\",\"prompt\":\"dark cyberpunk beat, 140 bpm\"}"

echo Done.
pause
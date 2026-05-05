@echo off
setlocal

echo Starting A2CR...
echo API:       http://localhost:8000
echo Dashboard: http://localhost:8501
echo API docs:  http://localhost:8000/docs
echo.

REM Start FastAPI in background
start "A2CR API" cmd /c "uvicorn main:app --host 127.0.0.1 --port 8000 >> logs\api.log 2>&1"

REM Wait for API to be ready
timeout /t 3 /nobreak > nul

REM Start Streamlit (foreground - closing this window stops the dashboard)
streamlit run dashboard/app.py --server.port 8501 --server.headless true

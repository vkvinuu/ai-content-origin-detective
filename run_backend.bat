@echo off
title AI Content-Origin Detective - Backend
cd /d "%~dp0backend"
echo ========================================================
echo Starting AI Content-Origin Detective Backend (FastAPI)
echo ========================================================
"%~dp0backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause

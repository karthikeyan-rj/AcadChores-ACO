@echo off
cd /d "C:\Users\santhosh raj\projects\Acad\backend"
"C:\Users\santhosh raj\projects\Acad\venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1

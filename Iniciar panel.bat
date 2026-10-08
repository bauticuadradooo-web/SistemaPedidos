@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo No encuentro el entorno de Python .venv. Revisá el README.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause

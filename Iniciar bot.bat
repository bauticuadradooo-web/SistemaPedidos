@echo off
cd /d "%~dp0"
if not exist ".env" (
  echo No existe el archivo .env. Copialo desde .env.example y cargá el token de BotFather.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m app.telegram_bot
pause

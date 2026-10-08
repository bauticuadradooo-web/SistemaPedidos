@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo No encuentro el entorno de Python .venv. Revisá el README.md.
  pause
  exit /b 1
)
if not exist ".env" (
  echo No existe el archivo .env. Crealo desde .env.example y cargá el token de BotFather.
  pause
  exit /b 1
)
start "Dely Drinks - Panel" cmd /k ""%~dp0.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
timeout /t 2 /nobreak >nul
start "Dely Drinks - Bot" cmd /k ""%~dp0.venv\Scripts\python.exe" -m app.telegram_bot"
start "" "http://127.0.0.1:8000"
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "(Get-NetIPConfiguration | Where-Object {$_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq 'Up'} | Select-Object -First 1 -ExpandProperty IPv4Address).IPAddress"`) do set "LAN_IP=%%I"
echo.
echo Panel disponible en esta computadora: http://127.0.0.1:8000
if defined LAN_IP echo En la misma red Wi-Fi: http://%LAN_IP%:8000
echo Mantené abiertas las ventanas del Panel y del Bot.
echo Para detenerlos, cerrá cada ventana o presioná Ctrl+C dentro de ella.
pause

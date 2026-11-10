@echo off
rem Starts Red Tape Navigator on this computer and opens it in your browser.
rem Double-click this file. Close the two black windows to stop the app.
setlocal
set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"
set "VENV=%BACKEND%\.venv\Scripts"

if not exist "%VENV%\python.exe" (
  echo The Python environment was not found at %VENV%
  echo Set it up once as described in README.md section 7, then run this again.
  pause
  exit /b 1
)
if not exist "%FRONTEND%\node_modules" (
  echo The frontend packages are not installed. Run "npm install" in the frontend folder once.
  pause
  exit /b 1
)

echo Preparing the local database and rules...
pushd "%BACKEND%"
set "DATABASE_URL=sqlite+aiosqlite:///./dev_local.db"
"%VENV%\python.exe" -m alembic upgrade head
if errorlevel 1 ( echo Database setup failed. & popd & pause & exit /b 1 )
"%VENV%\python.exe" -m app.kb.seed_loader
popd

echo Starting the API on http://localhost:8000 ...
start "RTN API (port 8000)" /D "%BACKEND%" cmd /k "set DATABASE_URL=sqlite+aiosqlite:///./dev_local.db&& "%VENV%\python.exe" -m uvicorn app.main:app --port 8000"

echo Starting the website on http://localhost:3000 ...
start "RTN Website (port 3000)" /D "%FRONTEND%" cmd /k "npm run dev"

echo Waiting for the website to come up...
powershell -NoProfile -Command "for($i=0;$i -lt 90;$i++){ try { Invoke-WebRequest -UseBasicParsing http://localhost:3000/en -TimeoutSec 2 | Out-Null; exit 0 } catch { Start-Sleep 1 } }; exit 1"
start "" "http://localhost:3000/en"
echo Done. The app is open in your browser. You can close this window.
timeout /t 5 >nul
endlocal

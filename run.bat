@echo off
REM ============================================================
REM  Verid-iq local launcher (Windows)
REM  Double-click this file to start the app at http://127.0.0.1:8000
REM ============================================================

cd /d "%~dp0"

echo.
echo  ============================================
echo   Verid-iq  -  starting local server
echo  ============================================
echo.

REM --- 1. Find Python -----------------------------------------
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python is not installed or not on PATH.
    echo         Install Python 3.11+ from https://www.python.org/downloads/
    echo         and tick "Add python.exe to PATH" during install.
    echo.
    pause
    exit /b 1
)

REM --- 2. Create venv if missing ------------------------------
if not exist "venv\Scripts\python.exe" (
    echo [setup] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

REM --- 3. Install / update dependencies -----------------------
echo [setup] Installing dependencies ^(first run can take a minute^)...
venv\Scripts\python.exe -m pip install --quiet --upgrade pip
venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies. See messages above.
    pause
    exit /b 1
)

REM --- 4. Launch the app --------------------------------------
echo.
echo  ============================================
echo   Server starting at  http://127.0.0.1:8000
echo   Press CTRL+C in this window to stop.
echo  ============================================
echo.

venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

REM Keep the window open if uvicorn exits (e.g. an error)
echo.
echo [server stopped]
pause

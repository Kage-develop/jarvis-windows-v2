@echo off
chcp 65001 >nul
echo.
echo ========================================
echo        J.A.R.V.I.S Windows Setup
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found. Install Python 3.11+ from python.org.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo [OK] %%i

REM Virtual environment
if not exist "venv" (
    echo [*] Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

REM Private config file
if not exist "config\api_keys.json" (
    copy "config\api_keys.example.json" "config\api_keys.json" >nul
    echo [*] Created config\api_keys.json. Add your Gemini API key there.
)

echo [*] Installing packages...
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo.
echo ========================================
echo             Setup Complete
echo ========================================
echo.
echo To start JARVIS:
echo   venv\Scripts\activate.bat
echo   python main.py
echo.
set /p choice="Start now? (y/n): "
if /i "%choice%"=="y" python main.py

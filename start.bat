@echo off
setlocal enabledelayedexpansion

:: Minecraft Autonomous Builder - Automated Setup Script
:: This script installs all dependencies, sets up the environment, and starts required services

title Minecraft Autonomous Builder Setup
color 0A

echo.
echo ============================================
echo   Minecraft Autonomous Builder - Setup
echo ============================================
echo.

:: Get the directory where this script is located
cd /d "%~dp0"

:: Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Running with administrator privileges
) else (
    echo [INFO] Not running as administrator. Some operations may require elevation.
    echo.
)

:: Step 1: Check Python installation
echo [STEP 1/9] Checking Python installation...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python found: %PYTHON_VERSION%
echo.

:: Step 2: Create virtual environment
echo [STEP 2/9] Setting up Python virtual environment...
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    if %errorLevel% neq 0 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created successfully
) else (
    echo [INFO] Virtual environment already exists
)
echo.

:: Step 3: Activate virtual environment and install Python packages
echo [STEP 3/9] Installing Python dependencies...
call .venv\Scripts\activate.bat
if %errorLevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment!
    pause
    exit /b 1
)

echo Installing requirements from requirements.txt...
pip install -r requirements.txt --quiet
if %errorLevel% neq 0 (
    echo [WARNING] Some packages may have failed to install. Trying again with verbose output...
    pip install -r requirements.txt
)
echo Installing project in editable mode...
pip install -e . --quiet
if %errorLevel% neq 0 (
    echo [WARNING] Failed to install project in editable mode. Trying again with verbose output...
    pip install -e .
)
echo [OK] Python dependencies installed
echo.

:: Step 4: Check Node.js installation
echo [STEP 4/9] Checking Node.js installation...
node --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH!
    echo Please install Node.js 18+ from https://nodejs.org
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo [OK] Node.js found: %NODE_VERSION%
echo.

:: Step 5: Install Node.js dependencies for bot
echo [STEP 5/9] Installing Node.js dependencies...
cd bot
if not exist "node_modules" (
    echo Running npm install...
    call npm install
    if %errorLevel% neq 0 (
        echo [ERROR] Failed to install Node.js dependencies!
        pause
        exit /b 1
    )
    echo [OK] Node.js dependencies installed
) else (
    echo [INFO] Node modules already installed
    echo Checking for updates...
    call npm install
)
cd ..
echo.

:: Step 6: Build TypeScript bot
echo [STEP 6/9] Building Minecraft bot (TypeScript)...
cd bot
call npm run build
if %errorLevel% neq 0 (
    echo [WARNING] Bot build had some issues, but continuing...
) else (
    echo [OK] Bot built successfully
)
cd ..
echo.

:: Step 7: Initialize database
echo [STEP 7/9] Initializing database...
if not exist "data" (
    mkdir data
    echo [INFO] Created data directory
)
python scripts/init_db.py
if %errorLevel% neq 0 (
    echo [WARNING] Database initialization had issues, but continuing...
) else (
    echo [OK] Database initialized
)
echo.

:: Step 8: Check and start Ollama
echo [STEP 8/9] Checking Ollama service...
tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find /I "ollama.exe" >nul
if %errorLevel% neq 0 (
    echo [INFO] Ollama is not running. Attempting to start...
    
    :: Try to find ollama in common locations
    set "OLLAMA_PATH="
    if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
        set "OLLAMA_PATH=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
    ) else if exist "%PROGRAMFILES%\Ollama\ollama.exe" (
        set "OLLAMA_PATH=%PROGRAMFILES%\Ollama\ollama.exe"
    ) else where ollama >nul 2>&1 (
        for /f "delims=" %%i in ('where ollama') do set "OLLAMA_PATH=%%i"
    )
    
    if defined OLLAMA_PATH (
        echo Starting Ollama from: %OLLAMA_PATH%
        start "" "%OLLAMA_PATH%" serve
        timeout /t 5 /nobreak >nul
        echo [OK] Ollama service started
    ) else (
        echo [WARNING] Ollama executable not found!
        echo Please install Ollama from https://ollama.ai
        echo.
        echo To continue without Ollama, you'll need to configure
        echo alternative LLM providers in the .env file.
    )
) else (
    echo [OK] Ollama is already running
)

:: Check if Ollama models are available
echo.
echo Checking Ollama models...
ollama list >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] No Ollama models found or Ollama not accessible
    echo.
    echo Recommended models to pull:
    echo   ollama pull llama3.2
    echo   ollama pull codellama
    echo   ollama pull mistral
    echo.
    set /p PULL_MODELS="Would you like to pull recommended models now? (Y/N): "
    if /i "!PULL_MODELS!"=="Y" (
        echo Pulling llama3.2...
        ollama pull llama3.2
        echo Pulling codellama...
        ollama pull codellama
        echo Pulling mistral...
        ollama pull mistral
        echo [OK] Models pulled successfully
    )
) else (
    echo [OK] Ollama models are available
    ollama list
)
echo.

:: Create .env file if it doesn't exist
echo Setting up environment configuration...
if not exist ".env" (
    echo [INFO] Creating .env file from template...
    (
        echo # LLM Configuration
        echo ARCHITECT_MODEL=ollama/llama3.2
        echo ENGINEER_MODEL=ollama/codellama
        echo OLLAMA_MODEL=mistral
        echo OLLAMA_BASE_URL=http://localhost:11434
        echo.
        echo # Optional: Cloud providers
        echo # OPENAI_API_KEY=sk-your-key-here
        echo # ANTHROPIC_API_KEY=sk-ant-your-key-here
        echo.
        echo # Application settings
        echo APP_ENV=development
        echo DATABASE_URL=sqlite:///data/mempalace.db
        echo BOT_API_URL=http://localhost:3001
        echo PYTHONPATH=.
    ) > .env
    echo [OK] .env file created
) else (
    echo [INFO] .env file already exists
)
echo.

:: Display setup completion message
echo.
echo ============================================
echo           SETUP COMPLETE!
echo ============================================
echo.
echo Your Minecraft Autonomous Builder is ready!
echo.
echo Next steps:
echo.
echo 1. Start Minecraft and open a world to LAN
echo    - Press Esc in-game
echo    - Click "Open to LAN"
echo    - Note the port number (usually 25565)
echo.
echo 2. Configure bot connection in bot/config.json:
echo    {
echo      "host": "localhost",
echo      "port": 25565,
echo      "username": "BuilderBot",
echo      "version": "1.20.4",
echo      "auth": "offline"
echo    }
echo.
echo 3. Start the API server:
echo    uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
echo.
echo 4. Start the Minecraft bot:
echo    cd bot
echo    npm run build
echo    node dist/index.js
echo.
echo 5. Open guide.html in your browser for detailed instructions!
echo.
echo ============================================
echo.

:: Ask if user wants to start services now
set /p START_SERVICES="Would you like to start the API server and bot now? (Y/N): "
if /i "!START_SERVICES!"=="Y" (
    echo.
    echo Starting API server and Minecraft bot...
    echo The API will be available at http://localhost:8000
    echo The bot will connect to your Minecraft server
    echo Press Ctrl+C to stop the servers
    echo.
    
    :: Start API server in background
    start "API Server" cmd /k "uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000"
    
    :: Wait a moment for API to start
    timeout /t 3 /nobreak >nul
    
    :: Start Minecraft bot
    cd bot
    start "Minecraft Bot" cmd /k "node dist/index.js"
    cd ..
    
    echo.
    echo Both services started in separate windows!
) else (
    echo.
    echo You can start the services later with:
    echo   API Server: uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
    echo   Minecraft Bot: cd bot ^&^& npm run build ^&^& node dist/index.js
    echo.
)

pause

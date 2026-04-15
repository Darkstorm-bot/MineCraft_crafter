# Windows Startup Scripts

This directory contains batch scripts to easily start the Minecraft Autonomous Builder services on Windows.

## Quick Start

### Option 1: Full Setup (First Time)
Run `start.bat` to:
- Install all Python and Node.js dependencies
- Build the TypeScript bot
- Initialize the database
- Check/start Ollama
- Configure environment variables
- Optionally start all services

### Option 2: Start Individual Services

#### Start API Server Only
```batch
start_api.bat
```
Starts the FastAPI server on http://localhost:8000

#### Start Minecraft Bot Only
```batch
start_bot.bat
```
Builds and starts the Minecraft bot

#### Start All Services
```batch
start_all.bat
```
Starts both the API server and Minecraft bot in separate windows

## Scripts Overview

| Script | Purpose |
|--------|---------|
| `start.bat` | Complete setup and installation |
| `start_api.bat` | Start only the API server |
| `start_bot.bat` | Start only the Minecraft bot |
| `start_all.bat` | Start both services together |

## Prerequisites

Before running these scripts, ensure you have:

1. **Python 3.11+** - Download from https://python.org
2. **Node.js 18+** - Download from https://nodejs.org
3. **Ollama** (optional but recommended) - Download from https://ollama.ai
   - Required models: `llama3.2`, `codellama`, `mistral`

## Configuration

### Environment Variables (.env)
The scripts will create a `.env` file automatically if it doesn't exist. You can customize:

```env
# LLM Configuration
ARCHITECT_MODEL=ollama/llama3.2
ENGINEER_MODEL=ollama/codellama
OLLAMA_MODEL=mistral
OLLAMA_BASE_URL=http://localhost:11434

# Application settings
APP_ENV=development
DATABASE_URL=sqlite:///data/mempalace.db
BOT_API_URL=http://localhost:3001
```

### Bot Configuration (bot/config.json)
Configure your Minecraft server connection:

```json
{
  "host": "localhost",
  "port": 25565,
  "username": "BuilderBot",
  "version": "1.20.4",
  "auth": "offline"
}
```

## Troubleshooting

### ModuleNotFoundError: No module named 'api'
This is fixed by the scripts which:
1. Set `PYTHONPATH` to the project root
2. Install the package in editable mode (`pip install -e .`)
3. Activate the virtual environment

If you still encounter this error:
1. Ensure you're running the script from the project root directory
2. Check that `.venv` exists and is activated
3. Run: `pip install -e .`

### Bot Build Fails
1. Ensure Node.js 18+ is installed
2. Delete `node_modules` and run `npm install`
3. Check for TypeScript errors in `bot/src/`

### Ollama Not Found
1. Install Ollama from https://ollama.ai
2. Pull required models:
   ```batch
   ollama pull llama3.2
   ollama pull codellama
   ollama pull mistral
   ```

### Port Already in Use
- API Server (8000): Change port in `start_api.bat`
- Bot API (3001): Update `BOT_API_URL` in `.env`
- Minecraft Server (25565): Change in `bot/config.json`

## Manual Startup (Alternative)

If you prefer not to use the batch scripts:

```batch
:: Activate virtual environment
.venv\Scripts\activate

:: Set PYTHONPATH
set PYTHONPATH=.

:: Install package
pip install -e .

:: Start API server
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

:: In another terminal, start the bot
cd bot
npm run build
node dist/index.js
```

## Service Architecture

```
┌─────────────────┐         ┌─────────────────┐
│   API Server    │◄───────►│  Minecraft Bot  │
│  (Port 8000)    │  HTTP   │  (Port 3001)    │
└────────┬────────┘         └────────┬────────┘
         │                           │
         │                           │
         ▼                           ▼
┌─────────────────┐         ┌─────────────────┐
│   MemPalace DB  │         │  Minecraft      │
│   (SQLite)      │         │  Server (LAN)   │
└─────────────────┘         └─────────────────┘
```

## Additional Resources

- `README.md` - Main project documentation
- `docs_runbook.md` - Operational procedures and troubleshooting
- `guide.html` - Interactive setup guide
- `/scripts/` - Additional utility scripts

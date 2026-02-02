# Mastermind - Multi-Agent Collaboration Platform

A workshop-ready platform where up to 5 AI personas can collaborate on problems together.

## Prerequisites

### Required
- **Git** - [Download](https://git-scm.com/downloads)
- **Python 3.11+** (3.13 recommended) - [Download](https://python.org)
- **Node.js 18+** (20+ recommended) - [Download](https://nodejs.org)
- **npm** (comes with Node.js)

### Optional (for advanced features)
- **Docker Desktop** - [Download](https://docker.com/products/docker-desktop)
  - Required for: Local Ollama models, code sandbox execution
- **Ollama** - [Download](https://ollama.ai) (alternative to Docker for local models)

### API Keys (optional if using MCP)
- [Anthropic API Key](https://console.anthropic.com/) - For Claude models
- [OpenAI API Key](https://platform.openai.com/) - For GPT models
- **Note:** API keys are not required if connecting via MCP (Model Context Protocol)

## Quick Start

```bash
# Clone the repository
git clone https://github.com/sethmblack/mastermind.git
cd mastermind

# Run the install script
chmod +x install.sh
./install.sh

# Optional: Add API key (not needed if using MCP)
# echo "ANTHROPIC_API_KEY=your_key_here" >> .env

# Start the application
./start.sh
```

Then open **http://localhost:3000** in your browser.

> **MCP Users:** If connecting via Claude Code or another MCP client, API keys are not required. The MCP server provides AI capabilities directly.

---

## Detailed Installation

### 1. Clone the Repository

```bash
git clone https://github.com/sethmblack/mastermind.git
cd mastermind
```

### 2. Run the Install Script

```bash
chmod +x install.sh
./install.sh
```

This will:
- Check all prerequisites are installed
- Clone the [AI-Personas](https://github.com/sethmblack/AI-Personas.git) library
- Set up the Python backend environment
- Install all Node.js frontend dependencies
- Create the `.env` configuration file

### 3. Configure API Keys

Edit the `.env` file and add your API key(s):

```bash
# Required: At least one API key
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional: OpenAI for GPT models
OPENAI_API_KEY=sk-your-key-here
```

### 4. Start the Application

```bash
./start.sh
```

### 5. Open in Browser

Navigate to: **http://localhost:3000**

---

## Manual Installation

If you prefer to install manually or the script fails:

### Step 1: Clone repositories

```bash
# Clone main project
git clone https://github.com/sethmblack/mastermind.git
cd mastermind

# Clone personas library
git clone https://github.com/sethmblack/AI-Personas.git personas
```

### Step 2: Setup Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate
# Activate (Windows)
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

cd ..
```

### Step 3: Setup Frontend

```bash
cd frontend
npm install
cd ..
```

### Step 4: Configure Environment

```bash
cp .env.example .env
# Edit .env and add your API keys
```

### Step 5: Run

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

---

## Docker Setup (Optional)

For running local models with Ollama or code sandbox:

### Using Docker Compose

```bash
# Start all services including Ollama
docker-compose up -d

# Or just start Ollama for local models
docker-compose up -d ollama
```

### Pull a local model (after Ollama is running)

```bash
docker exec -it mastermind-ollama-1 ollama pull llama3.2:3b
```

### Configure .env for local models

```bash
OLLAMA_BASE_URL=http://localhost:11434
```

---

## Verify Installation

### Check backend health:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status":"healthy","personas_loaded":262,"domains_available":40}
```

### Check available personas:
```bash
curl http://localhost:8000/api/personas/count
```

---

## Project Structure

```
mastermind/
├── backend/              # Python FastAPI server
│   ├── src/
│   │   ├── api/          # REST & WebSocket endpoints
│   │   ├── core/         # Orchestration engine
│   │   ├── db/           # SQLite database
│   │   ├── personas/     # Persona loader
│   │   └── providers/    # AI provider integrations
│   └── requirements.txt
├── frontend/             # React TypeScript app
│   ├── src/
│   │   ├── components/   # UI components
│   │   ├── hooks/        # React hooks
│   │   ├── store/        # Zustand state
│   │   └── lib/          # Utilities
│   └── package.json
├── personas/             # AI-Personas library (cloned)
├── docker-compose.yml    # Docker services
├── .env.example          # Environment template
├── install.sh            # Automated installer
├── start.sh              # Startup script
└── INSTALL.md            # This file
```

---

## Configuration Options

### Environment Variables (.env)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | No* | - | Anthropic API key for Claude |
| `OPENAI_API_KEY` | No | - | OpenAI API key for GPT models |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama server URL |
| `DATABASE_URL` | No | `sqlite:///./data/collab.db` | Database connection |
| `HOST` | No | `0.0.0.0` | Backend host |
| `PORT` | No | `8000` | Backend port |
| `DEBUG` | No | `true` | Enable debug mode |
| `MAX_PERSONAS_PER_SESSION` | No | `5` | Max personas per session |

*API keys are optional when connecting via MCP. Otherwise, at least one API key is required.

---

## Troubleshooting

### "No personas loaded"
```bash
# Check if personas directory exists
ls personas/experts/

# If missing, clone it manually
git clone https://github.com/sethmblack/AI-Personas.git personas
```

### "API key not configured"
```bash
# Verify .env exists and has your key
cat .env | grep API_KEY

# Make sure there are no extra spaces or quotes
ANTHROPIC_API_KEY=sk-ant-xxx  # Correct
ANTHROPIC_API_KEY="sk-ant-xxx"  # Wrong
```

### Backend won't start
```bash
# Check Python version (need 3.11+)
python3 --version

# Reinstall dependencies
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend won't start
```bash
# Check Node version (need 18+)
node --version

# Clear and reinstall
cd frontend
rm -rf node_modules
npm install
```

### Port already in use
```bash
# Find what's using the port
lsof -i :8000
lsof -i :3000

# Kill the process or use different ports
uvicorn src.main:app --port 8001
```

### Docker issues
```bash
# Check Docker is running
docker info

# Restart Docker services
docker-compose down
docker-compose up -d
```

---

## Development

### Run with auto-reload:

**Backend:**
```bash
cd backend && source venv/bin/activate
uvicorn src.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend && npm run dev
```

### Type checking:
```bash
cd frontend && npx tsc --noEmit
```

### Run tests:
```bash
cd backend && pytest
```

---

## Production Deployment

### Build frontend:
```bash
cd frontend
npm run build
```

### Run backend with multiple workers:
```bash
cd backend
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Docker:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

---

## Links

- **Repository:** https://github.com/sethmblack/mastermind
- **AI Personas:** https://github.com/sethmblack/AI-Personas
- **Issues:** https://github.com/sethmblack/mastermind/issues

## License

MIT

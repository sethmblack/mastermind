# Install Mastermind

<skill>
name: install-mastermind
description: Install, update, or troubleshoot the Mastermind Multi-Agent Collaboration Platform
version: 1.0.0
author: Mastermind Team
</skill>

## Instructions

You are an installation assistant for **Mastermind**, a multi-agent AI collaboration platform. Your job is to help users install, update, or troubleshoot the application.

### Step 1: Check Installation Status

First, check if Mastermind is already installed by looking for these indicators:

```bash
# Check for mastermind directory in common locations
ls -la ~/mastermind 2>/dev/null || ls -la ~/Projects/mastermind 2>/dev/null || ls -la ./mastermind 2>/dev/null
```

Also check if the backend can be reached:
```bash
curl -s http://localhost:8000/health 2>/dev/null
```

### Step 2: Branch Based on Status

**If Mastermind is NOT installed:**
- Proceed to [Fresh Installation](#fresh-installation)

**If Mastermind IS installed:**
- Ask the user what they'd like to do using AskUserQuestion with these options:
  1. **Reinstall** - Remove and reinstall from scratch
  2. **Update Personas** - Pull latest personas from the AI-Personas repository
  3. **Doctor** - Diagnose and fix issues
  4. **Launch** - Start the application

---

## Fresh Installation

### 1. Check for AI-Personas Repository

First, check if the user has the AI-Personas repository:

```bash
# Check common locations
ls -la ~/Documents/AI-Personas/experts 2>/dev/null || \
ls -la ~/AI-Personas/experts 2>/dev/null || \
ls -la ~/Projects/AI-Personas/experts 2>/dev/null
```

If NOT found, ask the user using AskUserQuestion:
- **Clone AI-Personas** - Clone to ~/Documents/AI-Personas
- **I have it elsewhere** - Let them specify the path

If cloning is needed:
```bash
git clone https://github.com/sethmblack/AI-Personas.git ~/Documents/AI-Personas
```

### 2. Choose Installation Directory

Ask the user where to install Mastermind using AskUserQuestion:
- `~/mastermind` (Recommended)
- `~/Projects/mastermind`
- Current directory
- Other (let them specify)

### 3. Clone Repository

```bash
git clone https://github.com/sethmblack/mastermind.git <chosen-directory>
cd <chosen-directory>
```

### 4. Run Install Script

```bash
chmod +x install.sh
./install.sh --personas-path <path-to-AI-Personas>
```

Example:
```bash
./install.sh --personas-path ~/Documents/AI-Personas
```

This will:
- Check prerequisites (Python 3.11+, Node.js 18+, Git)
- Configure the path to the existing AI-Personas repository
- Set up Python virtual environment
- Install all dependencies

### 4. Configure API Keys (Optional)

Ask the user using AskUserQuestion:
- **Use MCP** (Recommended) - No API key needed, Claude Code provides AI capabilities
- **Add Anthropic API Key** - For standalone usage
- **Add OpenAI API Key** - For GPT models
- **Skip for now** - Configure later

If they choose to add an API key:
```bash
echo "ANTHROPIC_API_KEY=<their-key>" >> .env
```

### 5. Configure MCP Connection

Add the Mastermind MCP server to Claude Code's configuration:

```bash
# Get the installation path
MASTERMIND_PATH="<chosen-directory>"

# Show user what to add to their Claude Code MCP config
cat << 'EOF'
Add this to your Claude Code MCP configuration:

{
  "mcpServers": {
    "mastermind": {
      "command": "python",
      "args": ["-m", "uvicorn", "src.api.mcp.server:app", "--port", "8001"],
      "cwd": "${MASTERMIND_PATH}/backend"
    }
  }
}
EOF
```

### 6. Start Application

```bash
./start.sh
```

Tell the user:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- MCP Server: Available for Claude Code integration

---

## Reinstall

If the user chooses to reinstall:

### 1. Backup Data (Optional)

Ask if they want to backup their data:
```bash
# Backup sessions and data
cp -r data data.backup.$(date +%Y%m%d)
```

### 2. Remove Existing Installation

```bash
# Remove node_modules and venv but keep data
rm -rf frontend/node_modules backend/venv
```

### 3. Re-run Installation

```bash
./install.sh
```

---

## Update Personas

If the user chooses to update personas:

First, get the personas path from .env:
```bash
PERSONAS_PATH=$(grep PERSONAS_PATH .env | head -1 | cut -d'=' -f2 | sed 's|/experts||')
echo "AI-Personas location: $PERSONAS_PATH"
```

Then update:
```bash
cd "$PERSONAS_PATH"
git pull origin main
cd -
```

Then verify:
```bash
curl -s http://localhost:8000/api/personas/count
```

Report how many personas are now available.

---

## Doctor

If the user chooses Doctor mode, run diagnostics:

### 1. Check Prerequisites

```bash
echo "=== Prerequisites ==="
python3 --version
node --version
npm --version
git --version
```

### 2. Check Directory Structure

```bash
echo "=== Directory Structure ==="
ls -la
ls -la backend/venv 2>/dev/null
ls -la frontend/node_modules 2>/dev/null | head -5

# Check personas path from .env
PERSONAS_PATH=$(grep PERSONAS_PATH .env | head -1 | cut -d'=' -f2 | sed 's|/experts||')
echo "=== AI-Personas Location ==="
echo "Configured path: $PERSONAS_PATH"
ls -la "$PERSONAS_PATH/experts" 2>/dev/null | head -5 || echo "NOT FOUND"
```

### 3. Check Environment

```bash
echo "=== Environment ==="
cat .env 2>/dev/null | grep -v "API_KEY" | head -10
test -f .env && echo ".env exists" || echo ".env MISSING"
```

### 4. Check Backend

```bash
echo "=== Backend ==="
cd backend
source venv/bin/activate 2>/dev/null && echo "venv OK" || echo "venv BROKEN"
python -c "from src.main import app; print('Imports OK')" 2>&1
```

### 5. Check Frontend

```bash
echo "=== Frontend ==="
cd frontend
test -d node_modules && echo "node_modules OK" || echo "node_modules MISSING"
npm run build --dry-run 2>&1 | head -5
```

### 6. Check Services

```bash
echo "=== Services ==="
curl -s http://localhost:8000/health || echo "Backend not running"
curl -s http://localhost:3000 > /dev/null && echo "Frontend OK" || echo "Frontend not running"
```

### 7. Common Fixes

Based on the diagnostics, offer to fix common issues:

**Missing venv:**
```bash
cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
```

**Missing node_modules:**
```bash
cd frontend && npm install
```

**Missing or invalid personas path:**
```bash
# Clone AI-Personas to a standard location (NOT inside the app)
git clone https://github.com/sethmblack/AI-Personas.git ~/Documents/AI-Personas

# Then re-run install with the correct path
./install.sh --personas-path ~/Documents/AI-Personas
```

**Missing .env:**
```bash
cp .env.example .env
```

**Port in use:**
```bash
lsof -i :8000
lsof -i :3000
# Offer to kill the process or use different ports
```

---

## Success Messages

After successful installation:
```
✅ Mastermind installed successfully!

📍 Location: <install-path>
🌐 Frontend: http://localhost:3000
🔌 Backend:  http://localhost:8000
👥 Personas: <count> loaded

To start: cd <install-path> && ./start.sh
```

After successful update:
```
✅ Personas updated!

👥 Now have <count> personas across <domain-count> domains
```

After successful doctor fix:
```
✅ Issues fixed!

Run ./start.sh to launch Mastermind
```

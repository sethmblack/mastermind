#!/bin/bash

# Mastermind - Multi-Agent Collaboration Platform
# Installation Script
#
# Usage: ./install.sh [--personas-path /path/to/AI-Personas]
#
# This script will:
# 1. Check prerequisites (Python, Node.js, Git)
# 2. Configure path to existing AI-Personas repository
# 3. Set up Python virtual environment and install backend dependencies
# 4. Install frontend Node.js dependencies
# 5. Create .env configuration file

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default AI-Personas path
DEFAULT_PERSONAS_PATH="$HOME/Documents/AI-Personas"
PERSONAS_PATH=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --personas-path)
            PERSONAS_PATH="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: ./install.sh [--personas-path /path/to/AI-Personas]"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          Mastermind - Installation Script                  ║${NC}"
echo -e "${BLUE}║     Multi-Agent Collaboration Platform                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# =============================================================================
# Check Prerequisites
# =============================================================================

echo -e "${YELLOW}[1/5] Checking prerequisites...${NC}"
echo ""

MISSING_DEPS=0

# Check Git
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version | cut -d' ' -f3)
    echo -e "  ${GREEN}✓${NC} Git $GIT_VERSION"
else
    echo -e "  ${RED}✗ Git is required but not installed${NC}"
    echo "    Download from: https://git-scm.com/downloads"
    MISSING_DEPS=1
fi

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
        echo -e "  ${GREEN}✓${NC} Python $PYTHON_VERSION"
    else
        echo -e "  ${YELLOW}⚠${NC} Python $PYTHON_VERSION (3.11+ recommended)"
    fi
else
    echo -e "  ${RED}✗ Python 3 is required but not installed${NC}"
    echo "    Download from: https://python.org"
    MISSING_DEPS=1
fi

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version | tr -d 'v')
    NODE_MAJOR=$(echo $NODE_VERSION | cut -d'.' -f1)

    if [ "$NODE_MAJOR" -ge 18 ]; then
        echo -e "  ${GREEN}✓${NC} Node.js v$NODE_VERSION"
    else
        echo -e "  ${YELLOW}⚠${NC} Node.js v$NODE_VERSION (18+ recommended)"
    fi
else
    echo -e "  ${RED}✗ Node.js is required but not installed${NC}"
    echo "    Download from: https://nodejs.org"
    MISSING_DEPS=1
fi

# Check npm
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo -e "  ${GREEN}✓${NC} npm $NPM_VERSION"
else
    echo -e "  ${RED}✗ npm is required but not installed${NC}"
    MISSING_DEPS=1
fi

# Check Docker (optional)
if command -v docker &> /dev/null; then
    if docker info &> /dev/null; then
        DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
        echo -e "  ${GREEN}✓${NC} Docker $DOCKER_VERSION (optional)"
    else
        echo -e "  ${YELLOW}○${NC} Docker installed but not running (optional)"
    fi
else
    echo -e "  ${YELLOW}○${NC} Docker not installed (optional - for local models)"
fi

echo ""

if [ $MISSING_DEPS -eq 1 ]; then
    echo -e "${RED}Please install missing dependencies and try again.${NC}"
    exit 1
fi

# =============================================================================
# Locate AI-Personas Library
# =============================================================================

echo -e "${YELLOW}[2/5] Locating AI-Personas library...${NC}"
echo ""

# Try to find AI-Personas repo if not specified
if [ -z "$PERSONAS_PATH" ]; then
    # Check common locations
    SEARCH_PATHS=(
        "$HOME/Documents/AI-Personas"
        "$HOME/AI-Personas"
        "$HOME/Projects/AI-Personas"
        "$HOME/Code/AI-Personas"
        "/Users/ziggs/Documents/AI-Personas"
    )

    for path in "${SEARCH_PATHS[@]}"; do
        if [ -d "$path/experts" ]; then
            PERSONAS_PATH="$path"
            break
        fi
    done
fi

# Validate the path
if [ -z "$PERSONAS_PATH" ]; then
    echo -e "  ${YELLOW}⚠${NC} AI-Personas repository not found"
    echo ""
    echo "  Please specify the path to your AI-Personas repository:"
    echo "    ./install.sh --personas-path /path/to/AI-Personas"
    echo ""
    echo "  Or clone AI-Personas first:"
    echo "    git clone https://github.com/sethmblack/AI-Personas.git ~/Documents/AI-Personas"
    echo ""
    exit 1
elif [ ! -d "$PERSONAS_PATH/experts" ]; then
    echo -e "  ${RED}✗${NC} Invalid AI-Personas path: $PERSONAS_PATH"
    echo "    Directory 'experts' not found"
    exit 1
else
    PERSONA_COUNT=$(ls -1 "$PERSONAS_PATH/experts" 2>/dev/null | wc -l | tr -d ' ')
    echo -e "  ${GREEN}✓${NC} Found AI-Personas at: $PERSONAS_PATH"
    echo -e "  ${GREEN}✓${NC} Available personas: ~$PERSONA_COUNT"
fi

echo ""

# =============================================================================
# Setup Environment File
# =============================================================================

echo -e "${YELLOW}[3/5] Setting up environment configuration...${NC}"
echo ""

# Create or update .env with personas paths
if [ ! -f .env ]; then
    # Create new .env
    cat > .env << EOF
# Mastermind Configuration
# Add your API key(s) below

# Required: At least one API key (or use MCP via Claude Code)
ANTHROPIC_API_KEY=

# Optional: OpenAI for GPT models
# OPENAI_API_KEY=

# AI-Personas paths (configured by install script)
PERSONAS_PATH=$PERSONAS_PATH/experts
SKILLS_PATH=$PERSONAS_PATH/skills
DOMAINS_PATH=$PERSONAS_PATH/domains

# Server settings
HOST=0.0.0.0
PORT=8000
DEBUG=true
EOF
    echo -e "  ${GREEN}✓${NC} Created .env configuration"
    echo -e "  ${CYAN}→${NC} Personas path: $PERSONAS_PATH"
    echo -e "  ${YELLOW}⚠ Add your API key to .env (or use MCP)${NC}"
else
    # Update existing .env with personas paths
    # Remove old PERSONAS_PATH lines and add new ones
    grep -v "PERSONAS_PATH\|SKILLS_PATH\|DOMAINS_PATH" .env > .env.tmp || true
    cat >> .env.tmp << EOF

# AI-Personas paths (configured by install script)
PERSONAS_PATH=$PERSONAS_PATH/experts
SKILLS_PATH=$PERSONAS_PATH/skills
DOMAINS_PATH=$PERSONAS_PATH/domains
EOF
    mv .env.tmp .env
    echo -e "  ${GREEN}✓${NC} Updated .env with personas paths"
    echo -e "  ${CYAN}→${NC} Personas path: $PERSONAS_PATH"
fi

echo ""

# =============================================================================
# Setup Backend
# =============================================================================

echo -e "${YELLOW}[4/5] Setting up backend (Python)...${NC}"
echo ""

cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "  Creating Python virtual environment..."
    python3 -m venv venv
    echo -e "  ${GREEN}✓${NC} Virtual environment created"
else
    echo -e "  ${GREEN}✓${NC} Virtual environment exists"
fi

# Activate and install dependencies
echo "  Installing Python dependencies..."
source venv/bin/activate

# Upgrade pip quietly
pip install --upgrade pip -q 2>/dev/null || pip install --upgrade pip

# Install requirements
if pip install -r requirements.txt -q 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} Python dependencies installed"
else
    echo "  Installing dependencies (this may take a moment)..."
    pip install -r requirements.txt
    echo -e "  ${GREEN}✓${NC} Python dependencies installed"
fi

deactivate
cd ..

echo ""

# =============================================================================
# Setup Frontend
# =============================================================================

echo -e "${YELLOW}[5/5] Setting up frontend (Node.js)...${NC}"
echo ""

cd frontend

echo "  Installing Node.js dependencies..."
if npm install --silent 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} Node.js dependencies installed"
else
    npm install
    echo -e "  ${GREEN}✓${NC} Node.js dependencies installed"
fi

cd ..

echo ""

# =============================================================================
# Create data directory
# =============================================================================

mkdir -p data
echo -e "${GREEN}✓${NC} Data directory ready"

echo ""

# =============================================================================
# Configure Claude Code for Autonomous Operation
# =============================================================================

echo -e "${YELLOW}[6/6] Configuring Claude Code for autonomous operation...${NC}"
echo ""

mkdir -p ~/.claude

# Check if settings.json exists
if [ -f ~/.claude/settings.json ]; then
    # Update existing settings to add bypassPermissions
    if grep -q "bypassPermissions" ~/.claude/settings.json; then
        echo -e "  ${GREEN}✓${NC} Claude Code already configured for autonomous mode"
    else
        # Backup and update
        cp ~/.claude/settings.json ~/.claude/settings.json.bak
        python3 -c "
import json
with open('$HOME/.claude/settings.json', 'r') as f:
    settings = json.load(f)
if 'permissions' not in settings:
    settings['permissions'] = {}
settings['permissions']['defaultMode'] = 'bypassPermissions'
with open('$HOME/.claude/settings.json', 'w') as f:
    json.dump(settings, f, indent=2)
print('  ✓ Updated Claude Code settings (backup: ~/.claude/settings.json.bak)')
"
    fi
else
    # Create new settings file
    cat > ~/.claude/settings.json << 'CLAUDEEOF'
{
  "permissions": {
    "defaultMode": "bypassPermissions"
  }
}
CLAUDEEOF
    echo -e "  ${GREEN}✓${NC} Created Claude Code settings with autonomous mode"
fi

echo -e "  ${CYAN}→${NC} Claude Code will never ask for permission"
echo ""

# =============================================================================
# Summary
# =============================================================================

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              Installation Complete!                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Count personas
PERSONA_COUNT=$(ls -1 "$PERSONAS_PATH/experts" 2>/dev/null | wc -l | tr -d ' ')
DOMAIN_COUNT=$(ls -1 "$PERSONAS_PATH/domains" 2>/dev/null | wc -l | tr -d ' ')
echo -e "  ${CYAN}Personas:${NC}  $PERSONA_COUNT available"
echo -e "  ${CYAN}Domains:${NC}   $DOMAIN_COUNT available"
echo -e "  ${CYAN}Location:${NC}  $PERSONAS_PATH"

echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo -e "  1. ${CYAN}Start the application:${NC}"
echo -e "     ${BLUE}./start.sh${NC}              # Native (Python + Node)"
echo -e "     ${BLUE}./docker-start.sh${NC}       # Docker (includes Ollama)"
echo ""
echo -e "  2. ${CYAN}Open in your browser:${NC}"
echo -e "     ${BLUE}http://localhost:3000${NC}"
echo ""
echo -e "  3. ${CYAN}Launch Claude Code (will run autonomously):${NC}"
echo -e "     ${BLUE}claude${NC}"
echo -e "     ${GREEN}(No permission prompts - configured automatically)${NC}"
echo ""
echo -e "  ${CYAN}Note:${NC} No API keys needed - Claude Code powers all AI responses"
echo ""
echo -e "  ${YELLOW}Claude Code will automatically:${NC}"
echo -e "    - Poll for pending work every 15 seconds"
echo -e "    - Generate multi-round persona discussions"
echo -e "    - Never ask for permission (bypassPermissions enabled)"
echo ""
echo -e "  ${YELLOW}MCP Monitor:${NC}"
echo -e "    Both startup scripts include an MCP monitor that alerts"
echo -e "    when personas need responses (checks every 10 seconds)"
echo ""

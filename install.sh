#!/bin/bash

# Mastermind - Multi-Agent Collaboration Platform
# Installation Script
#
# Usage: ./install.sh
#
# This script will:
# 1. Check prerequisites (Python, Node.js, Git)
# 2. Clone the AI-Personas library
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

# Repository URLs
PERSONAS_REPO="https://github.com/sethmblack/AI-Personas.git"

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
# Clone AI-Personas Library
# =============================================================================

echo -e "${YELLOW}[2/5] Setting up AI-Personas library...${NC}"
echo ""

if [ -d "personas" ] && [ -d "personas/experts" ]; then
    PERSONA_COUNT=$(ls -1 personas/experts 2>/dev/null | wc -l | tr -d ' ')
    echo -e "  ${GREEN}✓${NC} AI-Personas already installed (~$PERSONA_COUNT personas)"
else
    echo "  Cloning AI-Personas repository..."
    if git clone --depth 1 "$PERSONAS_REPO" personas 2>/dev/null; then
        PERSONA_COUNT=$(ls -1 personas/experts 2>/dev/null | wc -l | tr -d ' ')
        echo -e "  ${GREEN}✓${NC} AI-Personas cloned (~$PERSONA_COUNT personas)"
    else
        echo -e "  ${YELLOW}⚠${NC} Could not clone AI-Personas repository"
        echo "    You can clone it manually later:"
        echo "    git clone $PERSONAS_REPO personas"
    fi
fi

echo ""

# =============================================================================
# Setup Environment File
# =============================================================================

echo -e "${YELLOW}[3/5] Setting up environment configuration...${NC}"
echo ""

if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env

        # Update the personas path in .env
        if [ -d "personas/experts" ]; then
            # Use sed to update PERSONAS_PATH if it exists, or add it
            if grep -q "PERSONAS_PATH" .env; then
                sed -i.bak "s|# PERSONAS_PATH=.*|PERSONAS_PATH=$SCRIPT_DIR/personas/experts|" .env
                rm -f .env.bak
            fi
        fi

        echo -e "  ${GREEN}✓${NC} Created .env from template"
        echo -e "  ${YELLOW}⚠ Important: Add your API key to .env${NC}"
    else
        # Create minimal .env
        cat > .env << EOF
# Mastermind Configuration
# Add your API key(s) below

# Required: At least one API key
ANTHROPIC_API_KEY=

# Optional: OpenAI for GPT models
# OPENAI_API_KEY=

# Personas path (auto-configured)
PERSONAS_PATH=$SCRIPT_DIR/personas/experts

# Server settings
HOST=0.0.0.0
PORT=8000
DEBUG=true
EOF
        echo -e "  ${GREEN}✓${NC} Created .env configuration"
        echo -e "  ${YELLOW}⚠ Important: Add your API key to .env${NC}"
    fi
else
    echo -e "  ${GREEN}✓${NC} .env file already exists"
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
# Summary
# =============================================================================

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              Installation Complete!                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Count personas if available
if [ -d "personas/experts" ]; then
    PERSONA_COUNT=$(ls -1 personas/experts | wc -l | tr -d ' ')
    echo -e "  ${CYAN}Personas:${NC}  $PERSONA_COUNT available"
fi

echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo -e "  1. ${CYAN}Configure API keys (optional if using MCP):${NC}"
echo -e "     ${BLUE}ANTHROPIC_API_KEY=sk-ant-your-key-here${NC}"
echo -e "     ${CYAN}(Skip this step if connecting via Claude Code or MCP)${NC}"
echo ""
echo -e "  2. ${CYAN}Start the application:${NC}"
echo -e "     ${BLUE}./start.sh${NC}"
echo ""
echo -e "  3. ${CYAN}Open in your browser:${NC}"
echo -e "     ${BLUE}http://localhost:3000${NC}"
echo ""
echo -e "  ${CYAN}MCP Users:${NC} API keys not required - connect via Claude Code"
echo ""

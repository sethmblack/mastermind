#!/bin/bash

# Mastermind - Multi-Agent Collaboration Platform
# Start Script - Launches backend and frontend servers

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Multi-Agent Collaboration Platform - Starting...       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if .env exists (in backend/ or root)
if [ -f backend/.env ]; then
    ENV_FILE="backend/.env"
elif [ -f .env ]; then
    ENV_FILE=".env"
else
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please run ./install.sh first"
    exit 1
fi

# Load environment variables
export $(grep -v '^#' "$ENV_FILE" | xargs)

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down servers...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$MCP_MONITOR_PID" ]; then
        kill $MCP_MONITOR_PID 2>/dev/null || true
    fi
    # Kill any remaining processes
    pkill -f "uvicorn src.main:app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    pkill -f "mcp_monitor.sh" 2>/dev/null || true
    echo -e "${GREEN}Servers stopped${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start Backend
echo -e "${YELLOW}Starting backend server...${NC}"
cd backend
source venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo -n "  Waiting for backend"
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

# Verify backend started
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    HEALTH=$(curl -s http://localhost:8000/health)
    PERSONAS=$(echo $HEALTH | grep -o '"personas_loaded":[0-9]*' | cut -d':' -f2)
    DOMAINS=$(echo $HEALTH | grep -o '"domains_available":[0-9]*' | cut -d':' -f2)
    echo -e "${GREEN}✓${NC} Backend running on http://localhost:8000"
    echo -e "  ${CYAN}$PERSONAS personas loaded across $DOMAINS domains${NC}"
else
    echo -e "${RED}✗ Backend failed to start${NC}"
    echo "  Check the logs above for errors"
    cleanup
    exit 1
fi

echo ""

# Start Frontend
echo -e "${YELLOW}Starting frontend server...${NC}"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
echo -n "  Waiting for frontend"
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

# Verify frontend started
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Frontend running on http://localhost:3000"
else
    echo -e "${YELLOW}⚠${NC} Frontend may still be starting..."
fi

echo ""

# Start MCP Monitor
echo -e "${YELLOW}Starting MCP monitor...${NC}"
if [ -f "$SCRIPT_DIR/scripts/mcp_monitor.sh" ]; then
    "$SCRIPT_DIR/scripts/mcp_monitor.sh" &
    MCP_MONITOR_PID=$!
    echo -e "${GREEN}✓${NC} MCP monitor running (checking for pending work every 10s)"
else
    echo -e "${YELLOW}⚠${NC} MCP monitor script not found, skipping..."
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  Application Started!                       ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${CYAN}Frontend:${NC}  http://localhost:3000"
echo -e "  ${CYAN}Backend:${NC}   http://localhost:8000"
echo -e "  ${CYAN}API Docs:${NC}  http://localhost:8000/docs"
echo ""
echo -e "  ${CYAN}MCP Mode:${NC}  When enabled, monitor alerts when personas need responses"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all servers${NC}"
echo ""

# Open browser (optional - uncomment to enable)
# if command -v open &> /dev/null; then
#     open http://localhost:3000
# elif command -v xdg-open &> /dev/null; then
#     xdg-open http://localhost:3000
# fi

# Keep script running and wait for both processes
wait $BACKEND_PID $FRONTEND_PID

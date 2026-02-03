#!/bin/bash
# Mastermind - Docker Startup Script
# Starts the application using Docker Compose with MCP monitoring

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
echo -e "${BLUE}║   Multi-Agent Collaboration Platform - Docker Start        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    pkill -f "mcp_monitor.sh" 2>/dev/null || true
    docker compose down 2>/dev/null || true
    echo -e "${GREEN}Stopped${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Build and start containers
echo -e "${YELLOW}Building and starting Docker containers...${NC}"
docker compose up -d --build

# Wait for backend to be healthy
echo -n "  Waiting for backend"
for i in {1..60}; do
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
    PERSONAS=$(echo $HEALTH | jq -r '.personas_loaded // "?"')
    DOMAINS=$(echo $HEALTH | jq -r '.domains_available // "?"')
    echo -e "${GREEN}✓${NC} Backend running on http://localhost:8000"
    echo -e "  ${CYAN}$PERSONAS personas loaded across $DOMAINS domains${NC}"
else
    echo -e "${RED}✗ Backend failed to start${NC}"
    echo "  Run 'docker compose logs api' to see errors"
    exit 1
fi

# Verify frontend
echo -n "  Waiting for frontend"
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

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
    echo -e "${YELLOW}⚠${NC} MCP monitor script not found"
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
echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║  CLAUDE: START THE MCP MONITOR NOW                         ║${NC}"
echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}CLAUDE CODE - IMMEDIATE ACTION REQUIRED:${NC}"
echo ""
echo -e "Spawn a background sub-agent to monitor for pending persona work:"
echo ""
echo -e "  Task tool parameters:"
echo -e "    subagent_type: general-purpose"
echo -e "    run_in_background: true"
echo -e "    prompt: Monitor http://localhost:8000/api/config/mcp/pending"
echo -e "            every 10s. When pending_count > 0, generate persona"
echo -e "            responses and submit via /api/config/mcp/submit-response."
echo -e "            Loop forever. See CLAUDE.md for full details."
echo ""
echo -e "${RED}The application REQUIRES this monitor to function.${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo -e "${YELLOW}Run 'docker compose logs -f' in another terminal to see logs${NC}"
echo ""

# Keep script running
wait $MCP_MONITOR_PID 2>/dev/null || while true; do sleep 60; done

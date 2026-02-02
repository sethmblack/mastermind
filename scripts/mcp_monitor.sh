#!/bin/bash
# MCP Work Monitor - checks for pending work every 10 seconds
# When MCP mode is enabled and personas need responses, this script alerts

API_URL="${API_URL:-http://localhost:8000}"
CHECK_INTERVAL="${CHECK_INTERVAL:-10}"

# Colors
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}MCP Monitor started - checking every ${CHECK_INTERVAL}s${NC}"
echo -e "${CYAN}API URL: ${API_URL}${NC}"
echo ""

while true; do
  response=$(curl -s "${API_URL}/api/config/mcp/pending" 2>/dev/null)
  pending_count=$(echo "$response" | jq -r '.pending_count // 0' 2>/dev/null)

  if [ "$pending_count" != "0" ] && [ "$pending_count" != "null" ] && [ -n "$pending_count" ]; then
    echo ""
    echo -e "${YELLOW}════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}🔔 MCP WORK PENDING: $pending_count personas need responses${NC}"
    echo -e "${YELLOW}════════════════════════════════════════════════════════════${NC}"

    # Show session details
    echo "$response" | jq -r '.sessions[] | "Session: \(.session_name) (ID: \(.session_id))\n  Round: \(.round_number)/\(.max_rounds)\n  Pending: \(.pending_personas | join(", "))\n  Topic: \(.user_message[:80])..."' 2>/dev/null

    echo -e "${YELLOW}════════════════════════════════════════════════════════════${NC}"
    echo ""
  fi

  sleep "$CHECK_INTERVAL"
done

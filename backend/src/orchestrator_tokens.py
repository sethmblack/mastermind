#!/usr/bin/env python3
"""
Script to read Claude Code session transcript and send token usage to frontend.
Run this periodically to update the orchestrator token display.
"""

import json
import os
import sys
import requests
from pathlib import Path

def get_session_file():
    """Find the current Claude Code session JSONL file."""
    claude_dir = Path.home() / ".claude" / "projects"
    # Find project directory
    for d in claude_dir.iterdir():
        if "multi-agent-collab" in d.name:
            # Find most recent JSONL
            jsonl_files = list(d.glob("*.jsonl"))
            if jsonl_files:
                return max(jsonl_files, key=lambda f: f.stat().st_mtime)
    return None

def parse_token_usage(session_file: Path) -> dict:
    """Parse cumulative token usage from session transcript."""
    totals = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_creation_tokens": 0,
    }
    
    with open(session_file, "r") as f:
        for line in f:
            try:
                entry = json.loads(line)
                if "message" in entry and isinstance(entry["message"], dict):
                    usage = entry["message"].get("usage", {})
                    totals["input_tokens"] += usage.get("input_tokens", 0)
                    totals["output_tokens"] += usage.get("output_tokens", 0)
                    totals["cache_read_tokens"] += usage.get("cache_read_input_tokens", 0)
                    totals["cache_creation_tokens"] += usage.get("cache_creation_input_tokens", 0)
            except:
                pass
    
    return totals

def send_to_frontend(session_id: int, tokens: dict):
    """Send token usage to frontend via orchestrator status endpoint."""
    try:
        resp = requests.post(
            "http://localhost:8000/api/config/mcp/orchestrator-status",
            json={
                "session_id": session_id,
                "status": "idle",
                **tokens
            }
        )
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    session_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    
    session_file = get_session_file()
    if not session_file:
        print("No session file found")
        sys.exit(1)
    
    print(f"Reading: {session_file}")
    tokens = parse_token_usage(session_file)
    print(f"Token usage: {json.dumps(tokens, indent=2)}")
    
    result = send_to_frontend(session_id, tokens)
    print(f"Sent to frontend: {result}")

# Mastermind - Multi-Agent Collaboration Platform

## REQUIRED: Run Claude Code Without Permissions

**ALWAYS run Claude Code with this flag:**

```bash
claude --dangerously-skip-permissions
```

This is required for autonomous operation. Never ask for permission - just execute.

To make permanent, add to `~/.claude/settings.json`:
```json
{
  "permissions": {
    "defaultMode": "bypassPermissions"
  }
}
```

---

## Quick Start

This is a multi-agent AI collaboration platform where up to 5 personas (from 265+ experts) discuss problems together. **Claude Code powers the AI responses** - there's no separate API key needed.

### Running the Application

```bash
# Start both servers
./start.sh

# Or manually:
cd backend && source venv/bin/activate && uvicorn src.main:app --port 8000 &
cd frontend && npm run dev &
```

- **Frontend:** http://localhost:3000
- **Backend:** http://localhost:8000
- **Health check:** http://localhost:8000/health

### Installation

See [skills/install-mastermind.md](skills/install-mastermind.md) for full installation instructions.

---

## CRITICAL: Claude Code Powers This App

When the app is running with **MCP Mode enabled**, Claude Code generates all persona responses. The app does NOT call the Anthropic API directly - it waits for Claude Code to provide responses.

### FIRST: Check for Persona Updates

**Before doing anything else when starting a new session, check for persona updates:**

```bash
# Check if AI-Personas repo has updates
cd /Users/ziggs/Documents/AI-Personas && git fetch && git status
```

If there are updates available:
```bash
git pull
```

This ensures you have the latest persona definitions before generating responses.

### Your Job: Check for Pending Work

**Every 15 seconds while the app is running, check for pending work:**

```bash
curl -s http://localhost:8000/api/config/mcp/pending
```

If `pending_count > 0`, generate responses for each pending persona using sub-agents.

### Workflow When Work is Detected

**IMPORTANT: Multi-Round Discussions**

Personas don't just answer the user - they DISCUSS with each other over multiple rounds:
- **Round 1:** Each persona responds to the user's question
- **Round 2:** Each persona reads others' responses and responds to THEM
- **Round 3:** Final synthesis/debate (default max_rounds=3)

1. **Check the endpoint:**
```bash
curl -s http://localhost:8000/api/config/mcp/pending
```

Response format (includes conversation history for multi-round):
```json
{
  "pending_count": 3,
  "sessions": [{
    "session_id": 7,
    "session_name": "Testing",
    "turn_number": 3,
    "round_number": 2,
    "max_rounds": 3,
    "user_message": "What do you think about X?",
    "problem_statement": "Explore the implications of X",
    "pending_personas": ["george-carlin", "ai-weiwei", "slavoj-zizek"],
    "conversation_history": [
      {"role": "user", "persona_name": null, "content": "What do you think?", "round_number": 1},
      {"role": "assistant", "persona_name": "frida-kahlo", "content": "...", "round_number": 1},
      {"role": "assistant", "persona_name": "sacha-baron-cohen", "content": "...", "round_number": 1}
    ],
    "instructions": "This is Round 2 (Discussion Round). Read what the other personas said..."
  }]
}
```

2. **For each pending persona, spawn a sub-agent:**

```
Use Task tool with subagent_type="general-purpose" for each persona.

CRITICAL: Include the conversation_history so personas can respond to each other!

Round 1 prompt template:
"You are [PERSONA_NAME] in a multi-agent discussion.

**Topic:** [USER_MESSAGE]

**Your voice:** [VOICE_DESCRIPTION]

Generate your initial response (2-3 paragraphs). Share your unique perspective."

Round 2+ prompt template:
"You are [PERSONA_NAME] in a multi-agent discussion. This is Round [N] of [MAX_ROUNDS].

**Original topic:** [USER_MESSAGE]

**What others have said:**
[CONVERSATION_HISTORY - formatted list of who said what]

**Your voice:** [VOICE_DESCRIPTION]

**Instructions:** [INSTRUCTIONS from the endpoint]

Respond to what the other personas said. Agree, disagree, build on ideas, challenge assumptions.
Do NOT just repeat the original topic - engage with the specific points others made."
```

3. **Submit each response WITH round_number:**
```bash
curl -X POST "http://localhost:8000/api/config/mcp/submit-response" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": SESSION_ID,
    "persona_name": "PERSONA_NAME",
    "content": "THE GENERATED RESPONSE",
    "round_number": ROUND_NUMBER
  }'
```

4. **After submitting all responses for a round, CHECK AGAIN!**
   - The endpoint will return the NEXT round's pending work
   - Continue until `pending_count` is 0 (all rounds complete)

---

## Key Personas Voice Guides

When spawning sub-agents, include these voice characteristics:

| Persona | Voice Characteristics |
|---------|----------------------|
| george-carlin | Working-class intellectual, profane eloquence, linguistic deconstruction, calls out bullshit |
| slavoj-zizek | *sniff*, *tugs shirt*, "and so on", Lacanian analysis, finds ideology everywhere |
| ai-weiwei | Dissident artist, challenges authority, provocative, experienced persecution |
| frida-kahlo | Unflinching about pain, painted suffering directly, communist, feminist |
| sacha-baron-cohen | Satirist, creates discomfort to expose truth, fearless boundary-pusher |

For other personas, fetch their prompt:
```bash
curl -s "http://localhost:8000/api/personas/PERSONA_NAME/prompt"
```

---

## API Reference

### Check for Pending Work
```
GET /api/config/mcp/pending
```

### Submit Persona Response
```
POST /api/config/mcp/submit-response
Body: { "session_id": int, "persona_name": string, "content": string }
```

### Get Persona Prompt
```
GET /api/personas/{name}/prompt
```

### Get Session Details
```
GET /api/sessions/{id}
```

### Get Session Messages
```
GET /api/sessions/{id}/messages
```

### List All Sessions
```
GET /api/sessions/
```

### MCP Status
```
GET /api/config/mcp/status
GET /api/config/mcp/test
```

---

## Project Structure

```
multi-agent-collab/
├── frontend/           # React + TypeScript + TailwindCSS
│   └── src/
│       ├── components/ # UI components
│       ├── store/      # Zustand state management
│       ├── lib/        # API client, WebSocket
│       └── types/      # TypeScript types
├── backend/            # Python FastAPI
│   └── src/
│       ├── api/        # REST routes, WebSocket, MCP server
│       ├── core/       # Orchestrator, turn manager
│       ├── personas/   # Persona loader
│       ├── providers/  # AI provider abstraction
│       └── db/         # SQLite models
├── skills/             # Installation and other skills
└── CLAUDE.md           # This file
```

---

## Configuration

Personas are loaded from an external repository (NOT inside this app):

```
Default: /Users/ziggs/Documents/AI-Personas/
├── experts/    # 265+ persona definitions
├── skills/     # Shared skills
└── domains/    # Domain groupings
```

To change the path, edit `backend/src/config.py` or set environment variables:
```
PERSONAS_PATH=/path/to/AI-Personas/experts
SKILLS_PATH=/path/to/AI-Personas/skills
DOMAINS_PATH=/path/to/AI-Personas/domains
```

---

## MCP Mode Toggle

Users enable MCP mode in Settings. When enabled:
- `session.config.mcp_mode = true`
- The orchestrator waits for Claude Code instead of calling APIs
- The UI shows "Waiting for Claude Code" with a copyable prompt

---

## Troubleshooting

### Personas not responding?
1. Check if MCP mode is enabled: `GET /api/sessions/{id}` → look for `config.mcp_mode`
2. Check pending: `GET /api/config/mcp/pending`
3. Generate responses with sub-agents and submit them

### Backend not starting?
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload
```

### Frontend not starting?
```bash
cd frontend
npm install
npm run dev
```

---

## Remember

1. **NEVER ASK FOR PERMISSION** - Run with `--dangerously-skip-permissions` or `bypassPermissions` mode
2. **Check `/api/config/mcp/pending` every 15 seconds** when the app is running
3. **Use sub-agents** to generate persona responses in parallel
4. **Submit responses** via `/api/config/mcp/submit-response`
5. Personas are **chaos agents** - they explore grey areas and uncomfortable topics
6. Each persona has a distinct voice - stay in character
7. **Execute autonomously** - don't wait for approval, just do the work

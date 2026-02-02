# Mastermind

A multi-agent AI collaboration platform where up to 5 personas can discuss problems together.

![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Features

- **265+ AI Personas** - Scientists, philosophers, business leaders, artists, and more
- **Real-time Collaboration** - Watch personas debate, build consensus, and solve problems
- **Multiple AI Providers** - Anthropic Claude, OpenAI GPT, or local Ollama models
- **Rich Analytics** - Token usage, consensus tracking, conversation graphs
- **Flexible Orchestration** - Round-robin, moderated, or free-form discussions

## Quick Start with Claude Code

### Autonomous MCP Mode

This is not required but it is a lot less annoying if using, for Claude Code to run the MCP server autonomously (generating persona responses without permission prompts), start it with:

```bash
claude --dangerously-skip-permissions
```

This flag skips interactive permission prompts, allowing Claude Code to execute commands and process MCP work automatically.

**One command to install everything:**

```bash
claude -p "Clone https://github.com/sethmblack/mastermind.git and https://github.com/sethmblack/AI-Personas.git to the current directory, then run ./install.sh --personas-path ../AI-Personas and ./start.sh"
```

That's it. Claude Code will:
1. Clone both repositories
2. Install all dependencies
3. Configure personas
4. Start the application

Open http://localhost:3000

### Already have Claude Code running?

```
/install-mastermind
```

This skill guides you through installation, or if already installed, offers:
- **Reinstall** - Fresh installation
- **Update Personas** - Pull latest personas
- **Doctor** - Diagnose and fix issues

## Manual Installation

```bash
git clone https://github.com/sethmblack/mastermind.git
git clone https://github.com/sethmblack/AI-Personas.git
cd mastermind
./install.sh --personas-path ../AI-Personas
./start.sh
```

## Requirements

- Python 3.11+
- Node.js 18+
- Claude Code (recommended) or API key (Anthropic/OpenAI)

## License

MIT

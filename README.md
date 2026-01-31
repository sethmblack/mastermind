# Mastermind

A multi-agent AI collaboration platform where up to 5 personas can discuss problems together.

![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Features

- **265+ AI Personas** - Scientists, philosophers, business leaders, artists, and more
- **Real-time Collaboration** - Watch personas debate, build consensus, and solve problems
- **Multiple AI Providers** - Anthropic Claude, OpenAI GPT, or local Ollama models
- **Rich Analytics** - Token usage, consensus tracking, conversation graphs
- **Flexible Orchestration** - Round-robin, moderated, or free-form discussions

## Quick Start

```bash
git clone https://github.com/sethmblack/mastermind.git
cd mastermind
./install.sh
# Edit .env and add your ANTHROPIC_API_KEY
./start.sh
```

Open http://localhost:3000

## Documentation

See [INSTALL.md](INSTALL.md) for detailed installation instructions.

## Requirements

- Python 3.11+
- Node.js 18+
- API key (Anthropic or OpenAI) - *optional if using MCP*

## MCP Integration

This platform includes an MCP server for integration with Claude Code and other MCP clients. When connected via MCP, API keys are not required - the MCP client provides AI capabilities directly.

## License

MIT

# Flux Agent

**Flux Agent** is a local-first AI agent CLI for conversation, project planning, and hands-on development. It is designed to grow into an extensible automation platform with multi-agent orchestration, integrations, browser automation, deployment workflows, semantic project memory, and secure remote access from Android Termux.

## Current status

Flux Agent is under active development. The initial foundation includes:

- Interactive terminal with Chat, Plan, and Build modes.
- Groq chat-completions provider (Groq API key required for AI requests).
- Workspace-confined file listing, reading, and writing tools.
- Approval-gated shell command execution in the configured workspace.
- Local TOML configuration and environment-variable overrides.
- Provider fallback router for optional Gemini, Cerebras, and OpenRouter adapters.\n- Local SQLite project notes with full-text search.\n- Bounded multi-agent orchestration primitive and persistent workflow schedules.\n- Plugin manifest and installed CLI discovery, plus MCP stdio client foundation.\n- Optional Playwright browser controller and approved deployment CLI adapters.\n- Optional authenticated HTTPS remote API and Termux-friendly client.\n- Automated tests for core subsystems.

This is an early developer release. Several subsystems are foundations rather than end-to-end products: workflow workers, a public plugin marketplace, signed and sandboxed plugins, vector embeddings, OAuth integrations, complete remote execution, and production deployment verification remain under development. See [docs/ROADMAP.md](docs/ROADMAP.md).

## Quick start

Requires Python 3.11 or newer.

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Set your Groq API key as an environment variable:

```bash
# Linux/macOS
export GROQ_API_KEY="your_groq_api_key"
# Windows PowerShell
$env:GROQ_API_KEY="your_groq_api_key"
```

Then start Flux:

```bash
flux
```

You can also run `python -m flux_agent` from the source checkout. Run `flux doctor` to inspect the local setup.

## Modes and commands

- `/chat` — normal conversation.
- `/plan` — produce a plan without changing files.
- `/build` — enable workspace tools; file writes and shell commands require confirmation.
- `/mode` — show mode descriptions.
- `/tools` — list available tools.
- `/model` — show the configured model.
- `/settings` — show local settings.
- `/help` — show command help.
- `/exit` — exit the interactive session.

Ordinary requests should be written in natural language.

## Configuration

Flux reads optional settings from the platform configuration directory. Set `FLUX_CONFIG` to use a specific TOML file. Example:

```toml
[flux]
provider = "groq"
model = "openai/gpt-oss-120b"
workspace = "."
request_timeout = 90
max_tool_rounds = 8\nfallback_providers = ["gemini", "cerebras", "openrouter"]
```

`GROQ_API_KEY`, `FLUX_MODEL`, `FLUX_WORKSPACE`, and comma-separated `FLUX_FALLBACK_PROVIDERS` can be supplied through environment variables. Optional provider keys are `GEMINI_API_KEY`, `CEREBRAS_API_KEY`, and `OPENROUTER_API_KEY`. Copy `.env.example` to `.env` for local development if desired. `.env` is ignored by Git. Never commit API keys.

## Safety

Build-mode file operations are restricted to the configured workspace. File writes and shell commands require interactive confirmation. Shell commands run with the permissions of the current operating-system user; approval does not make an unsafe command safe. Use a disposable workspace for untrusted projects, and do not run Flux with elevated privileges unless absolutely necessary.

## Roadmap

1. Foundation, CLI, configuration, and Groq provider.
2. Execution engine, workspace tools, Git support, and stronger command isolation.
3. Model intelligence router and optional providers (Gemini, Cerebras, OpenRouter).
4. Multi-agent orchestration, task queues, and verification.
5. Local semantic project memory.
6. Integration Hub: MCP, external CLIs, APIs, webhooks, and plugins.
7. Browser automation and workflow scheduler.
8. Deployment engine and diagnostics.
9. Secure remote access and Termux client, plus Android-native compatibility evaluation.
10. Security hardening, cross-platform packaging, documentation, and release testing.

Optional extras: `pip install -e ".[browser]"` for Playwright or `pip install -e ".[remote]"` for the remote API. Install the browser binary with `playwright install chromium`.\n\nUseful commands include `flux memory-add "Project uses Python 3.12"`, `flux memory-search "Python"`, `flux integrations`, `flux remote-submit "Run tests"`, and `flux remote-tasks`.\n\nSee [SETUP.md](SETUP.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

## License

MIT. See [LICENSE](LICENSE).

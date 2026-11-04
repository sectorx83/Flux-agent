# Flux Agent

**Flux Agent** is a local-first AI agent CLI for conversation, project planning, and hands-on development. It is designed to grow into an extensible automation platform with multi-agent orchestration, integrations, browser automation, deployment workflows, semantic project memory, and secure remote access from Android Termux.

## Current status

Flux Agent is under active development. The initial foundation includes:

- Interactive terminal with Chat, Plan, and Build modes.
- Groq chat-completions provider (Groq API key required for AI requests).
- Workspace-confined file listing, reading, and writing tools.
- Approval-gated shell command execution in the configured workspace.
- Local TOML configuration and environment-variable overrides.
- Basic setup diagnostics and automated tests.

The broader capabilities in the roadmap are planned and should not be mistaken for implemented features yet.

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
model = "llama-3.3-70b-versatile"
workspace = "."
request_timeout = 90
max_tool_rounds = 8
```

`GROQ_API_KEY`, `FLUX_MODEL`, and `FLUX_WORKSPACE` can be supplied through environment variables. Copy `.env.example` to `.env` for local development if desired. `.env` is ignored by Git. Never commit API keys.

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

See [SETUP.md](SETUP.md) for installation and development instructions.

## License

MIT. See [LICENSE](LICENSE).

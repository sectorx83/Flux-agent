# Flux Agent

**Flux Agent** is a local-first AI agent CLI for conversation, project planning, and hands-on development. Its long-term direction is a general automation and development platform with multi-agent orchestration, integrations, browser automation, deployment workflows, project memory, and secure remote access from Android Termux.

## Current implementation

The current developer build includes:

- Interactive Chat, Plan, and Build modes.
- Groq as the primary chat-completions provider, with optional Gemini, Cerebras, and OpenRouter adapters.
- Workspace-confined file listing, reading, and writing, plus approval-gated shell execution.
- Local TOML configuration and environment-variable overrides.
- SQLite project notes with full-text search.
- A bounded multi-agent orchestration primitive.
- Persistent one-shot and interval workflow schedule records.
- Plugin manifest discovery, local CLI discovery, and an MCP stdio client foundation.
- Optional Playwright browser control and approved deployment CLI adapters.
- An optional authenticated HTTPS remote API and Termux-friendly client.
- Automated tests for the foundational subsystems.

This is an early developer release, not a finished autonomous platform. Workflow workers, true embedding-backed semantic memory, a public signed plugin marketplace, OAuth integrations, complete remote task execution, hardened sandboxing, and production deployment verification remain unfinished. See [docs/ROADMAP.md](docs/ROADMAP.md).

## Quick start

Requires Python 3.11 or newer.

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Set your Groq API key:

```bash
# Linux/macOS
export GROQ_API_KEY="your_groq_api_key"
# Windows PowerShell
$env:GROQ_API_KEY="your_groq_api_key"
```

Start Flux:

```bash
flux
```

Run `flux doctor` to inspect the local setup.

## Modes

- `/chat` — normal conversation.
- `/plan` — create a plan without changing files.
- `/build` — use workspace tools; file writes and shell commands require confirmation.

Natural language is the normal interface. Useful commands include:

```bash
flux init .
flux doctor
flux integrations
flux plugins
flux memory-add "The project uses Python and pytest"
flux memory-search "pytest"
flux workflow-add "nightly-check" '{"task":"run tests"}' "2026-11-05T02:00:00+00:00"
flux workflow-list
flux workflow-cancel 1
```

A workflow schedule is stored locally; a scheduler worker is still required to execute it.

## Provider configuration

Set optional fallback providers in your TOML configuration:

```toml
[flux]
provider = "groq"
model = "openai/gpt-oss-120b"
workspace = "."
request_timeout = 90
max_tool_rounds = 8
fallback_providers = ["gemini", "cerebras", "openrouter"]
```

Or use `FLUX_FALLBACK_PROVIDERS=gemini,cerebras,openrouter`. Provider keys are `GROQ_API_KEY`, `GEMINI_API_KEY`, `CEREBRAS_API_KEY`, and `OPENROUTER_API_KEY`. Only configure providers you actually use. Never commit keys.

## Optional features

- Browser: `pip install -e ".[browser]"` then `playwright install chromium`.
- Remote API: `pip install -e ".[remote]"`.
- Termux remote client: configure `FLUX_REMOTE_URL` with an HTTPS endpoint and `FLUX_REMOTE_TOKEN` with a high-entropy token, then use `flux remote-submit "Check the build" --mode plan` and `flux remote-tasks`.

The current remote API queues requests for inspection. It does not yet execute them through a background agent worker. Keep the host behind a private VPN or an HTTPS reverse proxy; never expose it directly to the public internet.

See [SETUP.md](SETUP.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), and [docs/ROADMAP.md](docs/ROADMAP.md).

## Safety

Build-mode file operations are restricted to the configured workspace. File writes and shell commands require interactive confirmation. Shell commands run with the permissions of the current operating-system user; approval is not a sandbox. Plugin discovery reads manifests but does not execute plugin code. MCP server commands are executable programs and must only be configured from trusted sources.

## License

MIT. See [LICENSE](LICENSE).

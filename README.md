# Flux Agent

**Flux Agent** is a local-first AI agent and automation CLI for conversation, planning, software development, and remote task execution. It is designed as a general-purpose tool for developers and everyday power users.

## Features

- **Three working modes:** Chat for conversation, Plan for structured plans, and Build for approved workspace edits and command execution.
- **Multiple AI providers:** Groq is the default, with optional Gemini, Cerebras, and OpenRouter fallbacks.
- **Tool execution:** list and read project files, write files after confirmation, and run shell commands after confirmation.
- **Project memory:** persistent SQLite notes with full-text search, scoped to the active workspace.
- **Multi-agent Build tool:** delegate up to four independent subtasks to parallel specialist agents and collect their results.
- **Workflow automation:** persistent one-shot and recurring schedules, with a foreground worker that executes due workflows.
- **Remote access:** authenticated HTTPS task submission from another device, including Android Termux, backed by a persistent SQLite queue and a host-side worker.
- **Browser automation:** optional Playwright controller with explicit approval for navigation and page interactions.
- **Integration foundations:** MCP stdio client, local CLI discovery, and plugin manifest registry.
- **Deployment adapters:** optional Vercel, Docker, and GitHub CLI deployment commands with explicit approval.
- **Terminal experience:** Rich-powered interactive interface and one-shot CLI commands.

Some larger integrations remain extension points rather than finished connectors. Flux does not currently ship a public plugin marketplace, OAuth app suite, or embedding-based vector memory. See [docs/ROADMAP.md](docs/ROADMAP.md) for the exact status.

## Quick start

Requires Python 3.11 or newer.

```bash
git clone https://github.com/sectorx83/Flux-agent.git
cd Flux-agent
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
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

## Interactive commands

- `/chat` — conversation mode.
- `/plan` — plan without changing files.
- `/build` — use workspace tools; file writes and shell commands require confirmation.
- `/mode`, `/tools`, `/model`, `/settings`, `/help`, `/exit` — inspect or control the session.

Useful CLI commands:

```bash
flux doctor
flux init .
flux integrations
flux plugins
flux memory-add "The project uses Python and pytest"
flux memory-search "pytest"
flux workflow-add "nightly-check" '{"task":"run the test suite","mode":"plan"}' "2026-11-05T02:00:00+00:00" --max-retries 3 --retry-delay 30
flux workflow-add "on-push" '{"task":"inspect recent changes","mode":"plan"}' "2026-11-05T02:00:00+00:00" --event-name git.push
flux workflow-trigger git.push
flux workflow-list
flux workflow-worker
flux remote-worker
```

A workflow payload contains a `task` string and an optional `mode` (`chat`, `plan`, or `build`). Run `flux workflow-worker` in a terminal to process due schedules. Workflows support bounded retries, retry-delay settings, named event triggers, and worker-console success/failure notifications. Trigger events locally with `flux workflow-trigger EVENT_NAME`, or send an authenticated `POST /workflows/events/{event_name}` request to the remote API using the same bearer token. Build-mode actions ask for approval in the worker terminal.

## Providers

Configure the primary provider and optional fallbacks in your TOML file:

```toml
[flux]
provider = "groq"
model = "openai/gpt-oss-120b"
workspace = "."
request_timeout = 90
max_tool_rounds = 8
fallback_providers = ["gemini", "cerebras", "openrouter"]
```

Environment keys: `GROQ_API_KEY`, `GEMINI_API_KEY`, `CEREBRAS_API_KEY`, and `OPENROUTER_API_KEY`. You only need keys for providers you use. Never commit API keys.

## Browser and deployment extras

```bash
python -m pip install -e ".[browser]"
playwright install chromium
```

Browser automation can also be used as a Python API via `BrowserAutomation`. Deployment adapters use installed `vercel`, `docker`, or `gh` CLIs and require explicit approval when called from code.

## Remote access and Termux

Install the remote extra on the host:

```bash
python -m pip install -e ".[remote]"
python -c "import secrets; print(secrets.token_urlsafe(48))"
export FLUX_REMOTE_TOKEN="paste-generated-token"
uvicorn flux_agent.remote.server:create_app --factory --host 127.0.0.1 --port 8765
```

In a second terminal on the host, run:

```bash
flux remote-worker
```

On Termux or another client, set `FLUX_REMOTE_URL` to the host's HTTPS URL and `FLUX_REMOTE_TOKEN` to the same high-entropy token:

```bash
flux remote-submit "Review the project and suggest fixes" --mode plan
flux remote-tasks
```

The API and worker share the persistent database at the platform data directory. Set `FLUX_REMOTE_DB` on the API and use the same database path for the worker only if you need a custom location. Keep the API on loopback behind a private VPN or a correctly configured HTTPS reverse proxy. Do not expose the bearer-token API directly to the public internet.

## Tests

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest
```

## Current limitations

- Project memory uses SQLite full-text search, not embeddings or a vector database.
- Build mode automatically decomposes complex independent work into bounded specialist tasks when appropriate. Specialists share read-only workspace file inspection tools; write and shell capabilities remain with the primary agent.
- Plugin support discovers and installs manifests only. It is not a public marketplace and does not execute third-party plugin code.
- MCP is a stdio client foundation; OAuth integrations for chat platforms, Google services, and project management tools are not bundled yet.
- Remote tasks persist across API restarts and are executed by a separate host worker. Device pairing, per-device identities, and session revocation are not implemented yet.
- Workflow schedules persist locally and require the foreground worker to run. They support bounded retries, named event triggers, an authenticated webhook endpoint, and worker-console notifications.

## Safety model

Flux is not a sandbox. It runs with the permissions of the operating-system account that launches it. Workspace file tools resolve paths under the configured workspace, and file writes, shell commands, browser actions, and deployments require approval in the relevant interactive flow. These approval prompts are not an operating-system security boundary. Only install integrations and configure MCP servers from sources you trust. Keep credentials in environment variables or a local untracked `.env` file.

## License

MIT. See [LICENSE](LICENSE).

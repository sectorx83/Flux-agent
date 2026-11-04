# Flux Agent

**Flux Agent** is a local-first AI agent and automation CLI for conversation, planning, software development, and remote task execution. It is designed as a general-purpose tool for developers and everyday power users.

## Features

- **Three working modes:** Chat for conversation, Plan for structured plans, and Build for approved workspace edits and command execution.
- **Multiple AI providers:** Groq is the default, with optional Gemini, Cerebras, and OpenRouter fallbacks.
- **Tool execution:** list and read project files, write files after confirmation, and run shell commands after confirmation.
- **Project memory:** workspace-scoped SQLite notes with full-text search and optional local vector embeddings through FastEmbed.
- **Multi-agent Build tool:** delegate up to four independent subtasks to parallel specialist agents and collect their results.
- **Workflow automation:** persistent one-shot and recurring schedules, with a foreground worker that executes due workflows.
- **Remote access:** paired devices with individual revocable credentials, device-scoped task history, persistent execution queues, and live task-status streaming.
- **Browser automation:** optional Playwright controller with explicit approval for navigation and page interactions.
- **Official service connectors:** GitHub issues, Slack/Discord/Telegram messaging, Google Tasks, and Notion tasks, with credential checks and approval-gated Build actions.
- **Deployment adapters:** optional Vercel, Docker, and GitHub CLI deployment commands with explicit approval.
- **Terminal experience:** Rich-powered interactive interface and one-shot CLI commands.

Flux keeps service credentials in environment variables and calls the providers' official APIs. It does not currently host OAuth consent flows or a refresh-token vault. The public plugin marketplace and signed plugin packages remain future work. See [docs/ROADMAP.md](docs/ROADMAP.md) for the exact status.

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
python -m pip install -e ".[memory]"
flux memory-add "The project uses Python and pytest" --semantic
flux memory-reindex
flux memory-search "Which test runner does this project use?" --semantic
flux usage
flux usage-price openai/gpt-oss-120b 0.10 0.50
flux connector-status
flux connector-test github
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

Capability-aware routing checks each candidate model before sending a request. Known default models include chat and tool calling. Declare capabilities for custom models explicitly:

```toml
[flux.model_capabilities]
"my-provider/my-tool-model" = ["chat", "tool_calling"]
"my-provider/my-vision-model" = ["chat", "vision"]
```

Unknown models are treated conservatively as chat-only. Image requests require `vision`; Build tool calls require `tool_calling`.

Token usage is recorded locally when providers return usage metadata. Configure prices explicitly with `flux usage-price MODEL INPUT OUTPUT`, using a consistent currency unit per million tokens. Flux does not guess provider prices, so unpriced usage remains visible without a fabricated cost estimate.

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
flux remote-pair "Android phone" # Run with the host administrator token; save the one-time device token
flux remote-devices
flux remote-revoke DEVICE_ID
flux remote-submit "Review the project and suggest fixes" --mode plan
flux remote-tasks
flux remote-watch TASK_ID
```

The API and worker share the persistent task database at the platform data directory. Device credentials are stored separately in `remote-devices.sqlite3`; set `FLUX_REMOTE_DEVICE_DB` to override that path. Pair devices with the administrator token, then put the one-time device token in that device's `FLUX_REMOTE_TOKEN`. Device tokens can only view their own tasks. Revoke them from the host with `flux remote-revoke DEVICE_ID`. Use `flux remote-watch TASK_ID` to stream task status and the final result. Keep the API on loopback behind a private VPN or a correctly configured HTTPS reverse proxy. Do not expose the bearer-token API directly to the public internet.

## Tests

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest
```

## Current limitations

- Semantic memory is optional and runs locally with FastEmbed. Install `.[memory]`, use `memory-add --semantic`, or index existing notes with `memory-reindex`. Existing keyword search remains available.
- Build mode automatically decomposes complex independent work into bounded specialist tasks when appropriate. Specialists share read-only workspace file inspection tools; write and shell capabilities remain with the primary agent.
- Plugin support discovers and installs manifests only. It is not a public marketplace and does not execute third-party plugin code.
- Official connectors use provider-issued credentials: `GITHUB_TOKEN`, `SLACK_BOT_TOKEN`, `DISCORD_BOT_TOKEN`, `TELEGRAM_BOT_TOKEN`, `GOOGLE_ACCESS_TOKEN`, and `NOTION_TOKEN`. Google Tasks requires an access token with the Tasks API scope. Flux does not run OAuth consent flows or retain refresh tokens; obtain and rotate credentials through each provider.
- Remote tasks persist across API restarts and are executed by a separate host worker. Device pairing issues one-time credentials stored as hashes; device task history is isolated and credentials can be revoked. Task streaming uses server-sent events.
- Workflow schedules persist locally and require the foreground worker to run. They support bounded retries, named event triggers, an authenticated webhook endpoint, and worker-console notifications.

## Safety model

Flux is not a sandbox. It runs with the permissions of the operating-system account that launches it. Workspace file tools resolve paths under the configured workspace, and file writes, shell commands, browser actions, and deployments require approval in the relevant interactive flow. These approval prompts are not an operating-system security boundary. Only install integrations and configure MCP servers from sources you trust. Keep credentials in environment variables or a local untracked `.env` file.

## License

MIT. See [LICENSE](LICENSE).

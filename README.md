# Flux Agent

**Flux Agent** is a local-first AI agent and automation CLI for conversation, planning, software development, and remote task execution. It is designed as a general-purpose tool for developers and everyday power users.

## Features

- **Three working modes:** Chat for conversation, Plan for structured plans, and Build for approved workspace edits and command execution.
- **Multiple AI providers:** Groq is the default, with optional Gemini, Cerebras, and OpenRouter fallbacks.
- **Tool execution:** list and read project files, write files after confirmation, and run shell commands after confirmation.
- **Project memory:** workspace-scoped SQLite notes with full-text search and optional local vector embeddings through FastEmbed.
- **Multi-agent Build tool:** delegate up to four independent subtasks to parallel specialist agents and collect their results.
- **Workflow automation:** persistent one-shot and recurring schedules, with a foreground worker that executes due workflows.
- **Remote access and web dashboard:** a responsive midnight-themed control room for submitting chat/plan/build tasks and monitoring task history, backed by the same authenticated API, paired devices, revocable credentials, persistent execution queues, and live task-status streaming.
- **Browser automation:** optional Playwright controller with explicit approval for navigation and page interactions.
- **Official service connectors:** GitHub issues, Slack/Discord/Telegram messaging, Google Tasks, and Notion tasks, with credential checks and approval-gated Build actions.
- **Deployment operations:** approved Vercel, Docker, and GitHub CLI commands, deployment status inspection, and approval-gated Vercel and Docker Swarm rollback.
- **Signed plugins:** Ed25519-verified packages and a signed HTTPS catalog. Package contents are stored but never executed.
- **Environment management:** hidden-prompt secret entry and private local storage; variable values are never printed.
- **Terminal experience:** Rich-powered interactive interface and one-shot CLI commands.

Flux calls providers' official APIs and reads credentials from process environment, a local `.env`, or the private Flux environment store. OAuth consent and refresh-token lifecycle remain external responsibilities. Signed plugin packages are verified before storage, but plugin code is not executed. See [docs/ROADMAP.md](docs/ROADMAP.md) for the exact status. Plugin publisher and catalog instructions are in [docs/PLUGIN_CATALOG.md](docs/PLUGIN_CATALOG.md). Production deployment and recovery procedures are in [docs/OPERATIONS.md](docs/OPERATIONS.md), and automated security coverage is described in [docs/SECURITY_TESTING.md](docs/SECURITY_TESTING.md).

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
flux plugin-pack ./my-plugin ./dist/my-plugin.fluxplugin --private-key-file ./plugin-signing.key
flux plugin-install-package ./my-plugin.fluxplugin --public-key BASE64_TRUSTED_KEY
flux plugin-install my-plugin 1.0.0 --catalog https://plugins.example.org/catalog.json --public-key BASE64_TRUSTED_KEY
flux env-list
flux env-set GROQ_API_KEY
flux env-unset GROQ_API_KEY
flux deployment-status vercel DEPLOYMENT_URL
flux deployment-rollback DEPLOYMENT_URL
flux deployment-rollback production_api --provider docker-swarm
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

Open `http://127.0.0.1:8765/` or `http://127.0.0.1:8765/dashboard` to use the Flux web dashboard. Sign in with the remote administrator token (or a paired device token); the dashboard submits tasks to the existing queue and refreshes task status. The token is held in the browser tab session and cleared when you disconnect or close the session. Keep the API on loopback behind a private VPN or a correctly configured HTTPS reverse proxy for remote access.

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
- Plugin packages and catalogs use Ed25519 signatures and SHA-256 integrity checks. Install only when the signing public key is trusted out of band. Packages are stored as data; Flux does not execute plugin code.
- The plugin catalog is a signed HTTPS JSON index. `flux plugin-install ID VERSION --catalog URL --public-key BASE64_KEY` installs an exact catalog version. `flux plugin-install-package FILE --public-key BASE64_KEY` verifies a local package.
- `flux env-set KEY` stores a value through a hidden prompt in the platform config directory. On POSIX systems the directory is mode 0700 and the file is mode 0600. `flux env-list` displays names only; `flux env-unset KEY` requires confirmation. Existing process environment variables take precedence.
- `flux deployment-status` inspects Vercel deployments, Docker containers, and GitHub Actions runs through their official CLIs. `flux deployment-rollback` supports Vercel deployments and Docker Swarm services, and requires confirmation. Generic Docker container rollback and GitHub Actions rollback are not supported.
- Official connectors use provider-issued credentials: `GITHUB_TOKEN`, `SLACK_BOT_TOKEN`, `DISCORD_BOT_TOKEN`, `TELEGRAM_BOT_TOKEN`, `GOOGLE_ACCESS_TOKEN`, and `NOTION_TOKEN`. Google Tasks requires an access token with the Tasks API scope. Flux does not run OAuth consent flows or retain refresh tokens; obtain and rotate credentials through each provider.
- Remote tasks persist across API restarts and are executed by a separate host worker. Device pairing issues one-time credentials stored as hashes; device task history is isolated and credentials can be revoked. Task streaming uses server-sent events.
- Workflow schedules persist locally and require the foreground worker to run. They support bounded retries, named event triggers, an authenticated webhook endpoint, and worker-console notifications.

## Safety model

Flux is not a sandbox. It runs with the permissions of the operating-system account that launches it. Workspace file tools resolve paths under the configured workspace, and file writes, shell commands, browser actions, and deployments require approval in the relevant interactive flow. These approval prompts are not an operating-system security boundary. Only install integrations and configure MCP servers from sources you trust. Keep credentials in the private Flux environment store, process environment, or a local untracked `.env` file. Never commit secrets. Signed plugin verification does not make plugin code safe to execute; Flux currently does not execute plugin packages.

## License

MIT. See [LICENSE](LICENSE).

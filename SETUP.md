# Setup and development

## Requirements

- Python 3.11+
- A Groq API key for AI features
- Windows, Linux, or macOS

## Install from source

```bash
git clone https://github.com/sectorx83/Flux-agent.git
cd Flux-agent
python -m venv .venv
```

Activate the environment:

```bash
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install the core package and development dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Optional features:

```bash
python -m pip install -e ".[browser,remote]"
playwright install chromium
```

Set `GROQ_API_KEY` in your shell, or copy `.env.example` to `.env` for local development. Do not commit `.env`.

## Run

```bash
flux
flux doctor
```

The default workspace is the current directory. Set `FLUX_WORKSPACE` to change it. Set `FLUX_CONFIG` to select a TOML configuration file.

## Tests and lint

```bash
pytest
ruff check .
```

## Optional remote host

Install the remote extra and generate a high-entropy token:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
export FLUX_REMOTE_TOKEN="paste-generated-token"
uvicorn flux_agent.remote.server:create_app --factory --host 127.0.0.1 --port 8765
```

Keep the host bound to loopback unless it is protected by a private VPN or a properly configured HTTPS reverse proxy. Never expose the bearer-token API directly to the public internet. The API stores submitted tasks in SQLite. Run `flux remote-worker` in a second host terminal to execute queued tasks. Build-mode writes and commands request approval in that worker terminal.

On Termux, install Flux and configure `FLUX_REMOTE_URL` with an HTTPS URL and `FLUX_REMOTE_TOKEN` with the paired token. Then use:

```bash
flux remote-submit "Check my build" --mode plan
flux remote-tasks
```

Run `flux workflow-worker` in a terminal to execute due local schedules. Workflow payloads use a `task` field and optional `mode` (`chat`, `plan`, or `build`).

## Provider fallback

Set `fallback_providers = ["gemini", "cerebras", "openrouter"]` in the `[flux]` config table, or set `FLUX_FALLBACK_PROVIDERS=gemini,cerebras,openrouter`. Configure only the API keys you intend to use. Groq remains the primary provider by default.

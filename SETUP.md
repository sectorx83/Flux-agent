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

Install Flux and development dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"\n# Optional features:\npython -m pip install -e ".[browser,remote]"\nplaywright install chromium
```

Set `GROQ_API_KEY` in your shell, or copy `.env.example` to `.env` for local development. Do not commit `.env`.

## Run

```bash
flux
flux doctor
```

The default workspace is the current directory. Set `FLUX_WORKSPACE` to change it. A custom TOML configuration path can be selected with `FLUX_CONFIG`.

## Tests and lint

```bash
pytest
ruff check .
```

## Development notes

- Keep provider adapters behind a common interface.
- Keep all filesystem operations inside the configured workspace unless a future explicit permission flow authorizes otherwise.
- Do not log API keys, tokens, or secret environment variables.
- New integrations must declare capabilities and permissions.
- Network access, remote execution, deployments, and destructive operations require explicit user authorization.


## Optional remote host

Install the remote extra and set a high-entropy token:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
export FLUX_REMOTE_TOKEN="paste-generated-token"
uvicorn flux_agent.remote.server:create_app --factory --host 127.0.0.1 --port 8765
```

Keep the host bound to loopback unless it is protected by a private VPN or a properly configured HTTPS reverse proxy. Never expose the bearer-token API directly to the public internet. The current API queues requests for inspection; it does not yet execute them through the agent worker.

On Termux, install Flux and configure `FLUX_REMOTE_URL` with an HTTPS URL and `FLUX_REMOTE_TOKEN` with the paired token. Then use `flux remote-submit "Check my build" --mode plan` and `flux remote-tasks`.

## Provider fallback

Set `fallback_providers = ["gemini", "cerebras", "openrouter"]` in the `[flux]` config table, or set `FLUX_FALLBACK_PROVIDERS=gemini,cerebras,openrouter`. Configure only the API keys you intend to use. Groq remains the primary provider by default.

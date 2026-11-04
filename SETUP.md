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
python -m pip install -e ".[dev]"
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

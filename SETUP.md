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
python -m pip install -e ".[browser,remote,memory,plugins]"
playwright install chromium
```

Set `GROQ_API_KEY` in your shell, use `flux env-set GROQ_API_KEY` to store it privately, or copy `.env.example` to `.env` for local development. `flux env-list` lists stored names without showing values; `flux env-unset KEY` removes one after confirmation. Never commit `.env` or `secrets.json`.

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

On the host, configure the API administrator token in `FLUX_REMOTE_TOKEN`. On an administrator client, configure the HTTPS `FLUX_REMOTE_URL` and the administrator token, then run `flux remote-pair "Android phone"`. Copy the one-time token from the response. On Termux, set the same HTTPS URL and the device-specific token as `FLUX_REMOTE_TOKEN`. Device tokens are stored as hashes on the host, can only access their own tasks, and can be revoked with `flux remote-revoke DEVICE_ID`. Use `flux remote-watch TASK_ID` to stream status updates.

```bash
flux remote-submit "Check my build" --mode plan
flux remote-tasks
```

Run `flux workflow-worker` in a terminal to execute due local schedules. Workflow payloads use a `task` field and optional `mode` (`chat`, `plan`, or `build`). Use `--max-retries` and `--retry-delay` on `workflow-add` to configure retries. Add `--event-name EVENT` to wait for a named event, then trigger it with `flux workflow-trigger EVENT` or the authenticated remote API endpoint `POST /workflows/events/{event_name}`.

## Semantic memory

Install the optional local embedding engine:

```bash
python -m pip install -e ".[memory]"
flux memory-add "The service uses SQLite" --semantic
flux memory-search "What database does the service use?" --semantic
```

Existing notes can be embedded with `flux memory-reindex`. The first use downloads the configured FastEmbed model; embeddings are generated locally and are not sent to the chat provider.

## Official connectors

Set the relevant token variables in `.env` or your shell. Run `flux connector-status` to see configured credentials and `flux connector-test SERVICE` to verify one against its official API. Supported services are GitHub, Slack, Discord, Telegram, Google Tasks, and Notion tasks. Build-mode external actions always require interactive confirmation. Google Tasks uses an OAuth access token with the `https://www.googleapis.com/auth/tasks` scope. Flux does not implement provider consent screens or refresh-token storage.

## Usage and model capabilities

Use `flux usage` to inspect locally recorded token counts. Add exact model prices with `flux usage-price MODEL INPUT OUTPUT`, in a consistent currency unit per million tokens. Unknown prices remain unestimated. Custom model capabilities are declared in the `[flux.model_capabilities]` TOML table; unknown models are chat-only until explicitly declared.

## Signed plugins

Publishers can build packages with `flux plugin-pack SOURCE OUTPUT --private-key-file KEY_FILE`. Keep the base64-encoded raw Ed25519 private key protected and offline where possible. See [docs/PLUGIN_CATALOG.md](docs/PLUGIN_CATALOG.md) for key generation, catalog signing, and hosting details.

Install a signed local package with a trusted base64-encoded Ed25519 public key:

```bash
flux plugin-install-package ./example.fluxplugin --public-key BASE64_TRUSTED_KEY
```

Install an exact version from a signed HTTPS catalog:

```bash
flux plugin-install example-plugin 1.2.0 --catalog https://example.org/flux/catalog.json --public-key BASE64_TRUSTED_KEY
```

The catalog and package signatures must verify with the trusted key. The catalog entry also pins the package SHA-256 digest. Obtain the signing key from a trusted publisher through an independent channel. Packages are stored as data only; Flux does not execute plugin code.

## Deployment operations

Use `flux deployment-status PROVIDER TARGET` to inspect a Vercel deployment URL, Docker container ID, or GitHub Actions run ID. `flux deployment-rollback DEPLOYMENT_URL` requests an explicit confirmation and invokes Vercel rollback for the exact deployment. Docker and GitHub workflow rollback are not currently implemented.

## Provider fallback

Set `fallback_providers = ["gemini", "cerebras", "openrouter"]` in the `[flux]` config table, or set `FLUX_FALLBACK_PROVIDERS=gemini,cerebras,openrouter`. Configure only the API keys you intend to use. Groq remains the primary provider by default.


## Production operations and security

See [Production operations](docs/OPERATIONS.md) for credential handling, remote API deployment, backups, release procedures, and rollback limits. See [Security testing](docs/SECURITY_TESTING.md) for CI coverage and the threat model. For signed plugin publishing, see [Plugin catalogs](docs/PLUGIN_CATALOG.md).

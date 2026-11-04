# Production operations

This guide covers the operational boundaries of Flux Agent. Flux is a local-first agent, not a hosted multi-tenant service or an operating-system sandbox.

## Installation

Use Python 3.11 or newer and install only the extras needed by the host:

```bash
python -m pip install -e ".[remote,plugins]"
```

Optional extras are `browser`, `memory`, `remote`, and `plugins`. The core install does not require cryptography, FastEmbed, Playwright, or FastAPI.

## Credentials

Preferred options, in order:

1. Use the private Flux environment store: `flux env-set GROQ_API_KEY`.
2. Inject secrets from your operating system or deployment secret manager.
3. Use an untracked local `.env` file for development only.

The environment store uses atomic file replacement. On POSIX systems its directory is mode 0700 and its file is mode 0600. On Windows, protect the platform config directory with account-specific ACLs. Stored values are plaintext at rest, not encrypted. Use full-disk encryption and operating-system account controls where required. Existing process environment values take precedence over stored values and `.env` values.

`flux env-list` displays names only. Do not capture hidden prompts or terminal input in CI logs. Rotate credentials at their provider if they may have been exposed.

## Remote API

The remote API uses bearer credentials and persistent SQLite storage. Keep it bound to loopback:

```bash
uvicorn flux_agent.remote.server:create_app --factory --host 127.0.0.1 --port 8765
```

Place it behind a private VPN or a correctly configured HTTPS reverse proxy if remote access is required. Do not expose the API directly to the public internet. Use a high-entropy administrator token, pair each device separately, and revoke lost devices promptly. Device tokens are stored as hashes and scoped to their own task history.

The API and worker must use the same task database. Back up the task database and device credential database together. Treat backups as sensitive because task prompts and results may contain confidential project information.

## Plugins

Read [PLUGIN_CATALOG.md](PLUGIN_CATALOG.md) before publishing or installing packages. Trust signing public keys through a separate channel. Keep private signing keys offline or in a managed secret store and rotate keys deliberately.

Signature verification proves package integrity and publisher-key possession. It does not establish that code is safe. Flux stores package archives and validated manifests but does not execute plugin code. Do not manually execute untrusted package contents.

## Deployment operations

The deployment adapter calls installed provider CLIs directly without a shell. Mutating deployment commands require explicit approval.

- Vercel: inspect deployment status and roll back an exact deployment URL or ID.
- Docker: inspect a container's state. Docker Swarm services support `docker service rollback`.
- GitHub Actions: inspect a run's status. A universal rollback is not defined because workflows may deploy to unrelated systems.

Examples:

```bash
flux deployment-status vercel DEPLOYMENT_URL
flux deployment-rollback DEPLOYMENT_URL
flux deployment-status docker-build CONTAINER_ID
flux deployment-rollback production_api --provider docker-swarm
flux deployment-status github-workflow RUN_ID
```

Confirm the target and provider before approving a rollback. A successful CLI exit code means the provider accepted the request; verify the resulting deployment state separately.

## Workflows and workers

Schedules are stored locally in SQLite. Run `flux workflow-worker` continuously on a trusted host to process due work. A worker must be running for scheduled tasks to execute. Build-mode actions still request approval in the worker terminal; do not run an unattended Build worker unless its workspace and permissions are deliberately constrained.

## Backups and recovery

Back up the platform data directory, including workflow, memory, remote task, device, and usage databases. Back up the platform config directory separately because it contains the private environment store. Keep backups encrypted and access-controlled. Test restore procedures rather than assuming a successful copy is a recovery plan.

## Releases

Pushing a tag matching `v*` triggers the release workflow. It builds source and wheel distributions, validates metadata with Twine, smoke-tests wheel installation on Linux, Windows, and macOS, and creates a GitHub Release with generated notes. PyPI publishing is not configured. Review the release artifacts before distributing them.

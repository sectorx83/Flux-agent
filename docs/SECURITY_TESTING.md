# Security testing and verification

## Automated checks

The GitHub Actions CI workflow runs on pushes to `main` and uses:

- Ubuntu, Windows, and macOS.
- Python 3.11 and 3.12.
- Ruff lint checks.
- The complete pytest suite.
- A Linux/Python 3.11 source and wheel build plus wheel-install smoke test.

Run the same core checks locally:

```bash
python -m pip install -e ".[dev,remote,plugins]"
ruff check .
pytest
python -m pip install build
python -m build
```

The release workflow separately installs the built wheel on all three operating systems.

## Security regression areas

The test suite includes regression coverage for:

- Workspace path confinement and approval gates for file writes and shell execution.
- Remote bearer authentication, per-device task scoping, credential revocation, and task streaming.
- Signed plugin package verification, modified-file detection, unsafe archive paths, and signed catalog integrity.
- Deployment approval, exact-target rollback, and invalid provider responses.
- Private environment storage, protected variable names, corrupt-file preservation, and POSIX permissions.
- Integration credential handling and approval before external side effects.

Tests use deterministic fixtures and mocked provider CLIs/APIs. CI does not perform live provider deployments, send real messages, access production accounts, or validate credentials against external services.

## Threat model and limits

Flux executes tools with the operating-system permissions of the account that launches it. Workspace path checks and approval prompts are safeguards, not a sandbox. Run it under a dedicated least-privilege account and keep workspaces limited to the intended project.

Environment-store values are plaintext at rest, protected by filesystem permissions rather than application-level encryption. Use operating-system disk encryption and access controls. Do not commit credentials or signing keys.

Signed plugin verification confirms integrity relative to a trusted Ed25519 key. It does not sandbox or execute plugin code. Flux currently stores packages as data.

The remote API is intended for loopback or private-network deployment behind HTTPS. It is not hardened as a public multi-tenant internet service. Do not expose it directly to the public internet.

The CI matrix is not a substitute for dependency vulnerability scanning, penetration testing, live provider contract testing, or an independent security review. Those activities must be performed before operating a public hosted service or handling high-impact production workloads.

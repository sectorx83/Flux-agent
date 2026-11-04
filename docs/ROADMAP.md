# Flux Agent roadmap

## Phase 1: Core completion

- [x] Automatic task decomposition for complex Build-mode work
- [x] Shared read-only workspace tools for specialist agents
- [x] Browser automation integrated into the Build-mode model tool loop
- [x] Explicit approval for browser navigation and page interactions
- [x] Workflow retry policies with configurable limits and delays
- [x] Named workflow event triggers
- [x] Authenticated webhook endpoint for remote workflow events
- [x] Worker-console success and failure notifications
- [x] Regression tests for browser approvals, workflow retries, and event-triggered schedules
- [x] Updated setup, usage, architecture, and safety documentation

## Phase 2: Intelligence and connectivity

- [x] Embedding-backed semantic memory with an optional local FastEmbed provider and SQLite vector index
- [x] Official GitHub, Slack, Discord, Telegram, Google Tasks, and Notion task API integrations
- [x] Capability-aware model routing for chat, tool calling, and vision requirements
- [x] Local token usage tracking and explicit per-model cost estimates
- [x] Remote device pairing with hashed per-device credentials and revocation
- [x] Server-sent event task streaming, device-scoped task access, and credential revocation

## Phase 2 implementation notes

- Semantic embeddings are optional, generated locally, and model-versioned. Existing FTS keyword search remains available.
- Service credentials are environment-provided. Flux calls official APIs but does not host OAuth consent screens or manage refresh tokens.
- Model prices are user-supplied per million tokens. Unpriced requests are not assigned invented costs.
- Remote device credentials are shown once, stored as hashes, scoped to their own task history, and revocable by the administrator.

## Phase 3: Production and ecosystem

- [x] Ed25519-signed plugin packages with SHA-256 file integrity verification
- [x] Signed HTTPS plugin catalog with exact-version selection and trusted-key verification
- [x] Deployment status inspection for Vercel, Docker, and GitHub Actions
- [x] Approval-gated Vercel rollback for an exact deployment target
- [x] Approval-gated Docker Swarm service rollback
- [ ] GitHub Actions rollback orchestration (workflow-specific rollback behavior is not universal)
- [x] Private local environment store with atomic writes, restrictive POSIX permissions, hidden secret entry, and masked listing
- [x] CI test matrix for Windows, macOS, and Linux on Python 3.11 and 3.12
- [x] Tagged source/wheel builds, package validation, cross-platform install smoke tests, and GitHub release automation
- [x] Automated integration and security regression tests across supported operating systems
- [x] Developer setup, plugin publishing, release, security-testing, and production-operations documentation

Live provider deployments and real-account integration tests are not run in CI. GitHub Actions rollback remains workflow-specific and is not presented as a generic feature. The environment store protects files with operating-system permissions but does not encrypt secret values at rest.

Flux intentionally does not include an operating-system sandbox. It uses explicit approvals and workspace path checks, but tools run with the permissions of the launching user. Those controls are guardrails, not isolation.

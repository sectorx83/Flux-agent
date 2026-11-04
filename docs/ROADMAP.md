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

- [ ] Signed plugin packages and a public plugin catalog
- [ ] Deployment status verification and rollback orchestration
- [ ] Environment management
- [ ] Cross-platform packaging and release automation
- [ ] Comprehensive integration and security testing
- [ ] Complete developer and operator documentation

Flux intentionally does not include an operating-system sandbox. It uses explicit approvals and workspace path checks, but tools run with the permissions of the launching user. Those controls are guardrails, not isolation.

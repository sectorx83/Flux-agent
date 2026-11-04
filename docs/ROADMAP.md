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

- [ ] Embedding-backed semantic memory with an optional local embedding provider and vector index
- [ ] Official Discord, Telegram, GitHub, Google, Slack, and task-management integrations
- [ ] Model capability-aware routing
- [ ] Usage tracking and cost reporting
- [ ] Remote device pairing and per-device credentials
- [ ] Remote task streaming and session revocation

## Phase 3: Production and ecosystem

- [ ] Signed plugin packages and a public plugin catalog
- [ ] Deployment status verification and rollback orchestration
- [ ] Environment management
- [ ] Cross-platform packaging and release automation
- [ ] Comprehensive integration and security testing
- [ ] Complete developer and operator documentation

Flux intentionally does not include an operating-system sandbox. It uses explicit approvals and workspace path checks, but tools run with the permissions of the launching user. Those controls are guardrails, not isolation.

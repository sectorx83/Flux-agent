# Flux Agent roadmap

## Foundation
- [x] Python CLI and three primary modes
- [x] Groq provider
- [x] Workspace file tools and approval-gated shell
- [x] Local configuration and CI baseline

## Core platform expansion
- [x] Provider adapter foundation and fallback router
- [x] Permission policy primitives
- [x] Persistent SQLite project memory with full-text search
- [x] Bounded multi-agent task orchestration primitive
- [x] Persistent workflow schedule store
- [x] Plugin manifest discovery and CLI discovery
- [x] MCP stdio JSON-RPC client foundation
- [x] Optional Playwright browser controller
- [x] Approved deployment CLI adapters
- [x] Authenticated remote API foundation and HTTPS client for Termux

## Still required before production
- [ ] Integrate every subsystem into the interactive CLI and add end-to-end tests
- [ ] True embedding-backed semantic project memory
- [ ] Workflow worker daemon, event triggers, webhooks, retries, and notifications
- [ ] Signed plugin packages, isolated plugin execution, and public marketplace
- [ ] OAuth/API integrations for Discord, Telegram, GitHub, Google, Slack, and others
- [ ] Remote pairing, revocation, task execution/streaming, TLS/VPN setup automation
- [ ] Browser approval UX, download/upload controls, and hardened browser profiles
- [ ] Sandboxed shell execution, audit logs, checkpoints, and rollback
- [ ] Deployment verification, rollback, and environment-secret handling
- [ ] Cross-platform packaging and security review

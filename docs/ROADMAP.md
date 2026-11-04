# Flux Agent roadmap

## Completed foundations
- [x] Python CLI with Chat, Plan, and Build modes
- [x] Groq provider and optional Gemini, Cerebras, and OpenRouter adapters
- [x] Workspace file tools and approval-gated shell commands
- [x] Local configuration and CI baseline
- [x] SQLite project notes with full-text search
- [x] Bounded asynchronous multi-agent orchestration primitive
- [x] Persistent one-shot and recurring workflow schedules
- [x] Foreground workflow worker for due schedules
- [x] Plugin manifest discovery and local CLI discovery
- [x] MCP stdio client foundation
- [x] Optional Playwright browser controller
- [x] Approved deployment CLI adapters
- [x] Authenticated HTTPS remote API, persistent task queue, and host-side worker

## Remaining product work
- [x] Integrate explicit multi-agent delegation into the interactive Build-mode tool loop
- [ ] Add automatic task decomposition and shared specialist tool access
- [ ] Add embedding-backed semantic memory as an optional provider, retaining local FTS fallback
- [ ] Add workflow event triggers, webhooks, retry policies, and notifications
- [ ] Build a signed plugin package format and public plugin catalog
- [ ] Add official OAuth/API integrations for Discord, Telegram, GitHub, Google, Slack, and task tools
- [ ] Add remote device pairing, per-device credentials, session revocation, and task streaming
- [ ] Integrate browser actions into the model tool loop with clear approval prompts
- [ ] Add deployment status verification, rollback orchestration, and environment management
- [ ] Add provider capability-aware routing, usage tracking, and cost reporting
- [ ] Finish cross-platform packaging, release automation, and broader integration tests

Flux intentionally does not include an operating-system sandbox. It uses explicit approvals and workspace path checks, but tools run with the permissions of the launching user. Those controls are convenience and guardrails, not isolation.

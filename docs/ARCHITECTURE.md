# Flux Agent architecture

Flux is local-first. The CLI owns the user session, the provider router owns model selection, and the tool layer owns local execution. Model output is never itself an authorization decision.

## Core layers

- **CLI and modes:** Chat, Plan, and Build.
- **Provider router:** Groq primary with optional Gemini, Cerebras, and OpenRouter adapters. Model capability declarations gate tool and vision requests; usage metadata is recorded locally with optional explicit price tables.
- **Execution tools:** workspace files, shell, Git, tests, and package managers.
- **Security:** permission policy, explicit approvals, workspace boundaries, timeouts, and audit-friendly task records.
- **Agents:** automatic decomposition of complex Build tasks into bounded specialists. Specialists share read-only workspace file tools; mutations remain with the primary agent.
- **Memory:** project-scoped SQLite notes with FTS5 keyword search and optional local FastEmbed vectors. Embeddings are model-versioned, stored as compact float blobs, and ranked with cosine similarity.
- **Integrations:** official GitHub, Slack, Discord, Telegram, Google Tasks, and Notion API adapters; credentials are read from environment variables. Build actions require confirmation. MCP stdio remains available. Plugin packages use Ed25519 signatures and signed HTTPS catalog metadata; packages are stored but not executed.
- **Environment:** application secrets can be stored in a private JSON file with atomic writes and restrictive POSIX permissions. Values are loaded only when absent from the process environment and are never shown by the management CLI.
- **Automation:** persistent one-shot, interval, and named event workflows with bounded retries and retry notifications. Authenticated webhook events can trigger waiting workflows.
- **Browser:** optional Playwright controller integrated into Build-mode tool calls for approved navigation and clicks plus page-text inspection.
- **Deployment:** approved wrappers around installed Vercel, Docker, and GitHub CLIs, status inspection for all three, and approved Vercel rollback.
- **Remote:** authenticated API with administrator pairing, hashed per-device tokens, device-scoped task visibility, revocation, and server-sent event task streaming.

## Trust boundaries

- A model may request a tool, but the host decides whether it is permitted.
- File tools must stay within the selected workspace.
- Shell, browser, deployment, and external submissions require user approval.
- Plugins are not trusted merely because they are installed.
- Remote API access requires a high-entropy administrator token and HTTPS. Paired device tokens are stored as SHA-256 hashes and can be revoked. Prefer a private VPN; never expose the API directly to the public internet.
- Service tokens are read from environment variables and are not stored by Flux. OAuth consent and refresh-token lifecycle are managed outside Flux.
- MCP server commands are executable programs and must be configured only from trusted sources.

## Remaining production work

In-app OAuth consent and refresh-token lifecycle, execution isolation through an OS/container sandbox, plugin execution and permission enforcement (not implemented), Docker and GitHub workflow rollback, additional provider-specific deployment verification, release signing/provenance, and expanded integration tests. Signed packages are integrity-verified but are not a sandbox or a safety guarantee.

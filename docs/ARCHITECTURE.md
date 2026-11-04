# Flux Agent architecture

Flux is local-first. The CLI owns the user session, the provider router owns model selection, and the tool layer owns local execution. Model output is never itself an authorization decision.

## Core layers

- **CLI and modes:** Chat, Plan, and Build.
- **Provider router:** Groq primary with optional Gemini, Cerebras, and OpenRouter adapters. Model capability declarations gate tool and vision requests; usage metadata is recorded locally with optional explicit price tables.
- **Execution tools:** workspace files, shell, Git, tests, and package managers.
- **Security:** permission policy, explicit approvals, workspace boundaries, timeouts, and audit-friendly task records.
- **Agents:** automatic decomposition of complex Build tasks into bounded specialists. Specialists share read-only workspace file tools; mutations remain with the primary agent.
- **Memory:** project-scoped SQLite notes with FTS5 keyword search and optional local FastEmbed vectors. Embeddings are model-versioned, stored as compact float blobs, and ranked with cosine similarity.
- **Integrations:** official GitHub, Slack, Discord, Telegram, Google Tasks, and Notion API adapters; credentials are read from environment variables. Build actions require confirmation. MCP stdio and metadata-only plugin manifests remain available.
- **Automation:** persistent one-shot, interval, and named event workflows with bounded retries and retry notifications. Authenticated webhook events can trigger waiting workflows.
- **Browser:** optional Playwright controller integrated into Build-mode tool calls for approved navigation and clicks plus page-text inspection.
- **Deployment:** approved wrappers around installed Vercel, Docker, and GitHub CLIs.
- **Remote:** authenticated API with administrator pairing, hashed per-device tokens, device-scoped task visibility, revocation, and server-sent event task streaming.

## Trust boundaries

- A model may request a tool, but the host decides whether it is permitted.
- File tools must stay within the selected workspace.
- Shell, browser, deployment, and external submissions require user approval.
- Plugins are not trusted merely because they are installed.
- Remote API access requires a high-entropy administrator token and HTTPS. Paired device tokens are stored as SHA-256 hashes and can be revoked. Prefer a private VPN; never expose the API directly to the public internet.
- Service tokens are read from environment variables and are not stored by Flux. OAuth consent and refresh-token lifecycle are managed outside Flux.
- MCP server commands are executable programs and must be configured only from trusted sources.

## Planned extensions

Encrypted credential vault, in-app OAuth consent and refresh-token lifecycle, marketplace signing, robust sandbox backends, deployment rollback orchestration, and cross-platform release packaging.

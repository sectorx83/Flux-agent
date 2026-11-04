# Flux Agent architecture

Flux is local-first. The CLI owns the user session, the provider router owns model selection, and the tool layer owns local execution. Model output is never itself an authorization decision.

## Core layers

- **CLI and modes:** Chat, Plan, and Build.
- **Provider router:** Groq primary with optional Gemini, Cerebras, and OpenRouter compatible adapters.
- **Execution tools:** workspace files, shell, Git, tests, and package managers.
- **Security:** permission policy, explicit approvals, workspace boundaries, timeouts, and audit-friendly task records.
- **Agents:** bounded specialist task delegation with concurrency limits.
- **Memory:** local SQLite project notes and full-text search. Embedding-backed semantic retrieval is a later extension; this release does not label keyword search as semantic embeddings.
- **Integrations:** manifest discovery, CLI discovery, and MCP stdio transport. Plugin manifests are inspected without executing plugin code.
- **Automation:** persistent one-shot and interval workflow schedule storage.
- **Browser:** optional Playwright browser controller.
- **Deployment:** approved wrappers around installed Vercel, Docker, and GitHub CLIs.
- **Remote:** optional authenticated API and Termux-friendly HTTPS client.

## Trust boundaries

- A model may request a tool, but the host decides whether it is permitted.
- File tools must stay within the selected workspace.
- Shell, browser, deployment, and external submissions require user approval.
- Plugins are not trusted merely because they are installed.
- Remote API access requires a high-entropy bearer token and HTTPS. Prefer a private VPN; never expose the API directly to the public internet.
- MCP server commands are executable programs and must be configured only from trusted sources.

## Planned extensions

Streaming responses, encrypted credential vault, richer OAuth integrations, vector embeddings, workflow triggers/webhooks, job worker lifecycle, marketplace signing, robust sandbox backends, remote task execution and result streaming, and cross-platform release packaging.

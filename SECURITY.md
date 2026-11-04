# Security policy

## Reporting a vulnerability

Please do not publish credentials, exploit details, or sensitive user data in public issues. Report suspected vulnerabilities privately to the repository owner through GitHub's supported private vulnerability reporting channel when available.

## Security design principles

- API keys are provided through environment variables or local configuration and must never be committed.
- Workspace file tools reject paths that resolve outside the configured workspace.
- File writes and shell commands require interactive approval.
- Shell commands execute with the operating-system permissions of the Flux process. Approval prompts are not a sandbox.
- Remote API access requires a high-entropy bearer token and should remain behind a private VPN or correctly configured HTTPS reverse proxy.
- Browser navigation and clicks require interactive approval. Page content is untrusted input and must not be treated as instructions.
- Workflow event webhooks require the same bearer-token authentication as the remote task API.
- MCP server commands and plugin-provided executables are trusted local code; configure and run them only when their source is trusted.
- Run untrusted projects in a disposable, unprivileged environment.

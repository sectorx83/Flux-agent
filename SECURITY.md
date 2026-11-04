# Security policy

## Reporting a vulnerability

Please do not publish credentials, exploit details, or sensitive user data in public issues. Report suspected vulnerabilities privately to the repository owner through GitHub's supported private vulnerability reporting channel when available.

## Security design principles

- API keys are provided through environment variables or local configuration and must never be committed.
- Workspace file tools reject paths that resolve outside the configured workspace.
- File writes and shell commands require interactive approval.
- Shell commands execute with the operating-system permissions of the Flux process. Approval prompts are not a sandbox.
- Remote access, plugins, browser automation, and deployment integrations are not enabled in this initial foundation.
- Run untrusted projects in a disposable, unprivileged environment.

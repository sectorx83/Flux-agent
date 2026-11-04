# Contributing

Contributions are welcome. Please keep changes focused and include tests for behavior changes.

## Development setup

Follow [SETUP.md](SETUP.md), then run:

```bash
pytest
ruff check .
```

## Contribution expectations

- Preserve the local-first design.
- Keep Groq as the required primary provider; optional providers must remain optional.
- Never commit API keys, tokens, or local `.env` files.
- Treat tool execution and integrations as security boundaries.
- Document new configuration options and user-facing commands.
- Do not claim a capability is implemented until it has tests and working behavior.

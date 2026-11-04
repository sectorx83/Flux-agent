"""Discover installed command-line integrations without invoking them."""

# isort: skip_file

import shutil


KNOWN_CLIS = ("git", "gh", "docker", "podman", "vercel", "npm", "pnpm", "yarn", "uv", "python", "node", "termux-wake-lock")


def discover_clis() -> dict[str, str | None]:
    return {name: shutil.which(name) for name in KNOWN_CLIS}

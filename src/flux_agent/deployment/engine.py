"""Explicitly approved deployment CLI adapters."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DeploymentResult:
    provider: str
    returncode: int
    output: str


class DeploymentEngine:
    COMMANDS = {
        "vercel": ("vercel", "deploy"),
        "docker-build": ("docker", "build"),
        "github-workflow": ("gh", "workflow", "run"),
    }

    def available(self) -> dict[str, bool]:
        binaries = {"vercel": "vercel", "docker-build": "docker", "github-workflow": "gh"}
        return {key: shutil.which(binary) is not None for key, binary in binaries.items()}

    def run(
        self, provider: str, workspace: Path, arguments: list[str], approved: bool = False
    ) -> DeploymentResult:
        if not approved:
            raise PermissionError("Deployment requires explicit user approval.")
        if provider not in self.COMMANDS:
            raise ValueError(f"Unsupported deployment provider: {provider}")
        binary = self.COMMANDS[provider][0]
        if shutil.which(binary) is None:
            raise FileNotFoundError(f"Required CLI is not installed: {binary}")
        if any("\x00" in arg for arg in arguments):
            raise ValueError("Invalid deployment argument.")
        command = [*self.COMMANDS[provider], *arguments]
        completed = subprocess.run(
            command, cwd=workspace.resolve(), capture_output=True, text=True,
            timeout=900, check=False,
        )
        return DeploymentResult(provider, completed.returncode, (completed.stdout + completed.stderr)[-30_000:])

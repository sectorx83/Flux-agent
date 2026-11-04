"""Approved deployment, status inspection, and rollback adapters."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DeploymentResult:
    provider: str
    returncode: int
    output: str


@dataclass(frozen=True, slots=True)
class DeploymentStatus:
    provider: str
    target: str
    state: str
    details: dict


class DeploymentEngine:
    COMMANDS = {
        "vercel": ("vercel", "deploy"),
        "docker-build": ("docker", "build"),
        "github-workflow": ("gh", "workflow", "run"),
    }

    def available(self) -> dict[str, bool]:
        binaries = {"vercel": "vercel", "docker-build": "docker", "github-workflow": "gh"}
        return {key: shutil.which(binary) is not None for key, binary in binaries.items()}

    @staticmethod
    def _validate_target(target: str) -> str:
        if not isinstance(target, str) or not target.strip() or "\x00" in target:
            raise ValueError("A non-empty deployment target is required.")
        return target.strip()

    @staticmethod
    def _run(command: list[str], workspace: Path, timeout: int = 120) -> subprocess.CompletedProcess:
        return subprocess.run(
            command, cwd=workspace.resolve(), capture_output=True, text=True,
            timeout=timeout, check=False,
        )

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
        if any(not isinstance(arg, str) or "\x00" in arg for arg in arguments):
            raise ValueError("Invalid deployment argument.")
        command = [*self.COMMANDS[provider], *arguments]
        completed = self._run(command, workspace, timeout=900)
        return DeploymentResult(provider, completed.returncode, (completed.stdout + completed.stderr)[-30_000:])

    def status(self, provider: str, target: str, workspace: Path) -> DeploymentStatus:
        target = self._validate_target(target)
        if provider == "vercel":
            command = ["vercel", "inspect", target, "--json"]
            binary = "vercel"
        elif provider == "docker-build":
            command = ["docker", "inspect", target, "--format", "{{json .State}}"]
            binary = "docker"
        elif provider == "github-workflow":
            command = ["gh", "run", "view", target, "--json", "status,conclusion,url,workflowName"]
            binary = "gh"
        else:
            raise ValueError(f"Unsupported deployment provider: {provider}")
        if shutil.which(binary) is None:
            raise FileNotFoundError(f"Required CLI is not installed: {binary}")
        completed = self._run(command, workspace)
        output = (completed.stdout + completed.stderr)[-30_000:]
        if completed.returncode:
            raise RuntimeError(f"{provider} status inspection failed: {output.strip()}")
        try:
            details = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"{provider} returned invalid status JSON.") from exc
        if not isinstance(details, dict):
            raise RuntimeError(f"{provider} returned an unexpected status response.")
        if provider == "vercel":
            state = str(details.get("readyState") or details.get("state") or details.get("status") or "unknown")
        elif provider == "docker-build":
            state = str(details.get("Status") or details.get("status") or "unknown")
        else:
            state = str(details.get("conclusion") or details.get("status") or "unknown")
        return DeploymentStatus(provider, target, state, details)

    def rollback(
        self, provider: str, target: str, workspace: Path, approved: bool = False
    ) -> DeploymentResult:
        if not approved:
            raise PermissionError("Deployment rollback requires explicit user approval.")
        target = self._validate_target(target)
        if provider != "vercel":
            raise ValueError("Rollback is currently supported only for Vercel deployments.")
        if shutil.which("vercel") is None:
            raise FileNotFoundError("Required CLI is not installed: vercel")
        completed = self._run(["vercel", "rollback", target], workspace, timeout=900)
        return DeploymentResult(provider, completed.returncode, (completed.stdout + completed.stderr)[-30_000:])

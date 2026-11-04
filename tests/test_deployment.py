from pathlib import Path

import pytest

from flux_agent.deployment.engine import DeploymentEngine


def test_deployment_requires_approval(tmp_path: Path):
    with pytest.raises(PermissionError, match="approval"):
        DeploymentEngine().run("vercel", tmp_path, [], approved=False)


def test_unknown_deployment_provider_rejected(tmp_path: Path):
    with pytest.raises(ValueError, match="Unsupported"):
        DeploymentEngine().run("unknown", tmp_path, [], approved=True)

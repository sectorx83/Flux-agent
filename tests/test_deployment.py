from pathlib import Path

import pytest

from flux_agent.deployment.engine import DeploymentEngine


def test_deployment_requires_approval(tmp_path: Path):
    with pytest.raises(PermissionError, match="approval"):
        DeploymentEngine().run("vercel", tmp_path, [], approved=False)


def test_unknown_deployment_provider_rejected(tmp_path: Path):
    with pytest.raises(ValueError, match="Unsupported"):
        DeploymentEngine().run("unknown", tmp_path, [], approved=True)



def test_vercel_deployment_status_parses_ready_state(tmp_path: Path, monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr("flux_agent.deployment.engine.shutil.which", lambda _binary: "/usr/bin/vercel")
    monkeypatch.setattr(
        "flux_agent.deployment.engine.subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0, stdout='{"readyState":"READY","url":"example.vercel.app"}', stderr=""
        ),
    )
    status = DeploymentEngine().status("vercel", "example.vercel.app", tmp_path)
    assert status.state == "READY"
    assert status.details["url"] == "example.vercel.app"


def test_deployment_status_rejects_invalid_json(tmp_path: Path, monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr("flux_agent.deployment.engine.shutil.which", lambda _binary: "/usr/bin/vercel")
    monkeypatch.setattr(
        "flux_agent.deployment.engine.subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout="not-json", stderr=""),
    )
    with pytest.raises(RuntimeError, match="invalid status JSON"):
        DeploymentEngine().status("vercel", "deployment.example", tmp_path)


def test_vercel_rollback_requires_approval_and_targets_exact_deployment(tmp_path: Path, monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr("flux_agent.deployment.engine.shutil.which", lambda _binary: "/usr/bin/vercel")
    commands = []

    def fake_run(command, **_kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=0, stdout="Rollback started", stderr="")

    monkeypatch.setattr("flux_agent.deployment.engine.subprocess.run", fake_run)
    engine = DeploymentEngine()
    with pytest.raises(PermissionError, match="approval"):
        engine.rollback("vercel", "deployment.example", tmp_path)
    result = engine.rollback("vercel", "deployment.example", tmp_path, approved=True)
    assert result.returncode == 0
    assert commands == [["vercel", "rollback", "deployment.example"]]


def test_rollback_rejects_unsupported_provider(tmp_path: Path):
    with pytest.raises(ValueError, match="supported for Vercel deployments and Docker Swarm services"):
        DeploymentEngine().rollback("docker-build", "container-id", tmp_path, approved=True)


def test_docker_swarm_rollback_requires_approval_and_validates_service(tmp_path: Path, monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr("flux_agent.deployment.engine.shutil.which", lambda _binary: "/usr/bin/docker")
    commands = []

    def fake_run(command, **_kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=0, stdout="Rollback initiated", stderr="")

    monkeypatch.setattr("flux_agent.deployment.engine.subprocess.run", fake_run)
    engine = DeploymentEngine()
    with pytest.raises(PermissionError, match="approval"):
        engine.rollback("docker-swarm", "api", tmp_path)
    with pytest.raises(ValueError, match="service name"):
        engine.rollback("docker-swarm", "--help", tmp_path, approved=True)
    result = engine.rollback("docker-swarm", "production_api", tmp_path, approved=True)
    assert result.returncode == 0
    assert commands == [["docker", "service", "rollback", "production_api"]]

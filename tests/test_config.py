from pathlib import Path

from flux_agent.config import load_config


def test_load_config_defaults(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("FLUX_MODEL", raising=False)
    monkeypatch.delenv("FLUX_WORKSPACE", raising=False)
    config = load_config(tmp_path / "missing.toml")
    assert config.provider == "groq"
    assert config.model
    assert config.workspace == Path.cwd().resolve()


def test_load_config_file(tmp_path: Path, monkeypatch) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[flux]\nmodel = "test-model"\nworkspace = "."\nmax_tool_rounds = 3\n',
        encoding="utf-8",
    )
    monkeypatch.delenv("FLUX_MODEL", raising=False)
    monkeypatch.delenv("FLUX_WORKSPACE", raising=False)
    config = load_config(config_file)
    assert config.model == "test-model"
    assert config.max_tool_rounds == 3



def test_load_model_capability_overrides(tmp_path: Path, monkeypatch) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[flux]\nmodel = "custom-model"\n'
        '[flux.model_capabilities]\n'
        'custom-model = ["chat", "tool_calling", "vision"]\n',
        encoding="utf-8",
    )
    monkeypatch.delenv("FLUX_MODEL", raising=False)
    config = load_config(config_file)
    assert config.model_capabilities["custom-model"] == ("chat", "tool_calling", "vision")


def test_load_config_rejects_unknown_model_capabilities(tmp_path: Path) -> None:
    import pytest

    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[flux]\n[flux.model_capabilities]\n'
        'custom-model = ["chat", "magic"]\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Unknown model capabilities"):
        load_config(config_file)

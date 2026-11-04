import pytest

from flux_agent.remote.client import RemoteClient


def test_remote_client_rejects_plain_http():
    with pytest.raises(ValueError, match="HTTPS"):
        RemoteClient("http://localhost:8765", "x" * 48)


def test_remote_client_requires_long_token():
    with pytest.raises(ValueError, match="32 characters"):
        RemoteClient("https://example.invalid", "short")

from flux_agent.providers.router import ProviderRouter


def test_unknown_provider_is_rejected():
    try:
        ProviderRouter("not-a-provider")
    except ValueError as exc:
        assert "Unknown provider" in str(exc)
    else:
        raise AssertionError("Unknown provider was accepted")


def test_groq_is_default_primary():
    router = ProviderRouter()
    assert router.active_provider == "groq"

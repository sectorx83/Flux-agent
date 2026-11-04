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



def test_usage_store_records_tokens_and_estimates_configured_cost(tmp_path):
    from flux_agent.usage.store import UsageStore

    store = UsageStore(tmp_path / "usage.sqlite3")
    store.set_price("example-model", 1.0, 2.0)
    store.record(
        "groq",
        "example-model",
        {"prompt_tokens": 1_000_000, "completion_tokens": 500_000, "total_tokens": 1_500_000},
    )
    summary = store.summary()
    assert summary[0]["provider"] == "groq"
    assert summary[0]["total_tokens"] == 1_500_000
    assert summary[0]["estimated_cost"] == 2.0
    assert store.totals()["requests"] == 1


def test_usage_store_leaves_cost_unknown_without_price(tmp_path):
    from flux_agent.usage.store import UsageStore

    store = UsageStore(tmp_path / "usage.sqlite3")
    store.record("groq", "unpriced-model", {"prompt_tokens": 10, "completion_tokens": 5})
    assert store.summary()[0]["estimated_cost"] is None


def test_usage_store_rejects_negative_prices_and_invalid_counts(tmp_path):
    import pytest

    from flux_agent.usage.store import UsageStore

    store = UsageStore(tmp_path / "usage.sqlite3")
    with pytest.raises(ValueError, match="negative"):
        store.set_price("model", -1, 1)
    with pytest.raises(ValueError, match="invalid"):
        store.record("groq", "model", {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 2})

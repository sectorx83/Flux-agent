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



def test_router_skips_models_without_tool_calling_capability():
    class FakeProvider:
        def __init__(self, model, result):
            self.model = model
            self.result = result
            self.calls = 0
            self.last_usage = {}
            self.last_model = model

        def chat(self, messages, tools=None):
            self.calls += 1
            return {"role": "assistant", "content": self.result}

    router = ProviderRouter("groq", ("gemini",))
    first = FakeProvider("chat-only", "wrong")
    second = FakeProvider("tool-model", "correct")
    router.providers = [("groq", first), ("gemini", second)]
    router.model_capabilities["chat-only"] = {"chat"}
    router.model_capabilities["tool-model"] = {"chat", "tool_calling"}

    result = router.chat([{"role": "user", "content": "inspect"}], tools=[{"type": "function"}])
    assert result["content"] == "correct"
    assert first.calls == 0
    assert second.calls == 1
    assert router.active_model == "tool-model"


def test_router_requires_vision_capability_for_image_messages():
    import pytest

    from flux_agent.providers.groq import ProviderError

    router = ProviderRouter("groq")
    router.providers = [("groq", type("Fake", (), {"model": "text-only"})())]
    router.model_capabilities["text-only"] = {"chat", "tool_calling"}
    with pytest.raises(ProviderError, match="vision"):
        router.chat(
            [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": "https://example.invalid/x"}}]}]
        )



def test_default_gemini_flash_model_is_eligible_for_vision():
    class FakeProvider:
        model = "gemini-2.5-flash"
        last_model = model
        last_usage = {}

        def chat(self, messages, tools=None):
            return {"role": "assistant", "content": "image understood"}

    router = ProviderRouter("gemini")
    router.providers = [("gemini", FakeProvider())]
    result = router.chat(
        [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": "https://example.invalid/image.png"}}]}]
    )
    assert result["content"] == "image understood"

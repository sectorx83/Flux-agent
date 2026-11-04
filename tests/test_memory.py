from pathlib import Path

from flux_agent.memory.store import MemoryStore


def test_memory_is_persisted_and_project_scoped(tmp_path: Path):
    store = MemoryStore(tmp_path / "memory.db")
    store.add("alpha", "The build uses Python and pytest", "decision")
    store.add("beta", "The project uses Rust and cargo", "note")
    assert len(store.search("alpha", "Python pytest")) == 1
    assert store.search("beta", "Python") == []



def test_semantic_memory_search_is_project_scoped_and_ranked(tmp_path: Path):
    store = MemoryStore(tmp_path / "memory.db")
    first = store.add("alpha", "Python web application deployment")
    second = store.add("alpha", "Rust embedded systems")
    other = store.add("beta", "Python web application deployment")
    store.set_embedding(first, "alpha", "test-model", [1.0, 0.0])
    store.set_embedding(second, "alpha", "test-model", [0.0, 1.0])
    store.set_embedding(other, "beta", "test-model", [1.0, 0.0])

    results = store.search_semantic("alpha", [0.9, 0.1], "test-model")
    assert [item["id"] for item in results] == [first, second]
    assert results[0]["score"] > results[1]["score"]
    assert all(item["id"] != other for item in results)


def test_semantic_memory_rejects_invalid_vectors_and_cascades_delete(tmp_path: Path):
    import pytest

    store = MemoryStore(tmp_path / "memory.db")
    memory_id = store.add("alpha", "A local note")
    with pytest.raises(ValueError, match="finite"):
        store.set_embedding(memory_id, "alpha", "test-model", [float("nan")])
    store.set_embedding(memory_id, "alpha", "test-model", [1.0, 0.0])
    assert store.delete(memory_id, "alpha")
    assert store.search_semantic("alpha", [1.0, 0.0], "test-model") == []


def test_unembedded_memory_listing_and_model_refresh(tmp_path: Path):
    store = MemoryStore(tmp_path / "memory.db")
    first = store.add("alpha", "First note")
    second = store.add("alpha", "Second note")
    assert [item["id"] for item in store.list_unembedded("alpha", "model-a")] == [first, second]
    store.set_embedding(first, "alpha", "model-a", [1.0, 0.0])
    assert [item["id"] for item in store.list_unembedded("alpha", "model-a")] == [second]
    assert [item["id"] for item in store.list_unembedded("alpha", "model-b")] == [first, second]



def test_existing_memory_database_rebuilds_full_text_index(tmp_path: Path):
    import sqlite3
    from datetime import UTC, datetime

    path = tmp_path / "legacy-memory.db"
    with sqlite3.connect(path) as db:
        db.execute(
            """CREATE TABLE memories (
                id INTEGER PRIMARY KEY, project TEXT NOT NULL, category TEXT NOT NULL,
                content TEXT NOT NULL, created_at TEXT NOT NULL
            )"""
        )
        db.execute(
            "INSERT INTO memories VALUES(1,?,?,?,?)",
            ("legacy-project", "decision", "Existing memory uses SQLite", datetime.now(UTC).isoformat()),
        )
    store = MemoryStore(path)
    results = store.search("legacy-project", "SQLite")
    assert len(results) == 1
    assert results[0]["content"] == "Existing memory uses SQLite"

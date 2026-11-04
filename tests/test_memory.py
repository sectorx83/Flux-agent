from pathlib import Path

from flux_agent.memory.store import MemoryStore


def test_memory_is_persisted_and_project_scoped(tmp_path: Path):
    store = MemoryStore(tmp_path / "memory.db")
    store.add("alpha", "The build uses Python and pytest", "decision")
    store.add("beta", "The project uses Rust and cargo", "note")
    assert len(store.search("alpha", "Python pytest")) == 1
    assert store.search("beta", "Python") == []

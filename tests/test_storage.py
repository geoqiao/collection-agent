import pytest
from src.storage.memory_store import MemoryStore
from src.core.models import UserState, UserProfile


@pytest.fixture
def store():
    return MemoryStore()


@pytest.fixture
def sample_state():
    return UserState(
        user_id="u001",
        profile=UserProfile(user_id="u001", name="张三")
    )


def test_save_and_load(store, sample_state):
    store.save(sample_state)
    loaded = store.load("u001")
    assert loaded is not None
    assert loaded.user_id == "u001"
    assert loaded.profile.name == "张三"


def test_load_nonexistent(store):
    assert store.load("nonexistent") is None


def test_load_all(store, sample_state):
    store.save(sample_state)
    store.save(UserState(user_id="u002", profile=UserProfile(user_id="u002", name="李四")))
    all_states = store.load_all()
    assert len(all_states) == 2

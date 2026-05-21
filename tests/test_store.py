"""Tests for token_ledger.store — uses a tmp_path so nothing touches ~/.config."""

from datetime import date, timedelta


from token_ledger.models import Entry, EntryType
from token_ledger import store


def make_entry(id="test-1", provider="openai", total=1_000_000) -> Entry:
    return Entry(
        id=id,
        provider=provider,
        type=EntryType.GRANT,
        total_tokens=total,
        expires=date.today() + timedelta(days=90),
    )


class TestStore:
    def test_load_empty(self, tmp_path):
        assert store.load(tmp_path) == []

    def test_save_and_load(self, tmp_path):
        e = make_entry()
        store.save([e], tmp_path)
        loaded = store.load(tmp_path)
        assert len(loaded) == 1
        assert loaded[0].id == e.id
        assert loaded[0].total_tokens == e.total_tokens

    def test_upsert_new(self, tmp_path):
        e = make_entry()
        store.upsert(e, tmp_path)
        assert len(store.load(tmp_path)) == 1

    def test_upsert_replace(self, tmp_path):
        e = make_entry()
        store.upsert(e, tmp_path)
        e.used_tokens = 500_000
        store.upsert(e, tmp_path)
        entries = store.load(tmp_path)
        assert len(entries) == 1
        assert entries[0].used_tokens == 500_000

    def test_upsert_multiple(self, tmp_path):
        store.upsert(make_entry("a"), tmp_path)
        store.upsert(make_entry("b"), tmp_path)
        store.upsert(make_entry("c"), tmp_path)
        assert len(store.load(tmp_path)) == 3

    def test_get_found(self, tmp_path):
        e = make_entry()
        store.upsert(e, tmp_path)
        found = store.get(e.id, tmp_path)
        assert found is not None
        assert found.id == e.id

    def test_get_not_found(self, tmp_path):
        assert store.get("nonexistent", tmp_path) is None

    def test_remove_existing(self, tmp_path):
        e = make_entry()
        store.upsert(e, tmp_path)
        result = store.remove(e.id, tmp_path)
        assert result is True
        assert store.get(e.id, tmp_path) is None
        assert store.load(tmp_path) == []

    def test_remove_nonexistent(self, tmp_path):
        result = store.remove("ghost", tmp_path)
        assert result is False

    def test_ledger_file_created(self, tmp_path):
        store.save([make_entry()], tmp_path)
        ledger = tmp_path / "ledger.yaml"
        assert ledger.exists()
        content = ledger.read_text()
        assert "entries:" in content
        assert "test-1" in content

    def test_load_idempotent(self, tmp_path):
        e = make_entry()
        store.save([e], tmp_path)
        a = store.load(tmp_path)
        b = store.load(tmp_path)
        assert len(a) == len(b) == 1

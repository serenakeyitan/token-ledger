"""CLI integration tests using Click's test runner."""

from datetime import date, timedelta
from pathlib import Path

import pytest
from click.testing import CliRunner

from token_ledger.cli import main
from token_ledger import store
from token_ledger.models import EntryType


@pytest.fixture
def runner(tmp_path):
    """Click test runner with isolated config dir."""
    r = CliRunner()
    r._config_dir = str(tmp_path)
    return r


def invoke(runner, args, config_dir=None):
    cd = config_dir or runner._config_dir
    return runner.invoke(main, ["--dir", cd] + args)


class TestAdd:
    def test_add_basic(self, runner, tmp_path):
        r = invoke(runner, [
            "add", "openai-yc",
            "--provider", "openai",
            "--type", "grant",
            "--total", "2M",
        ])
        assert r.exit_code == 0, r.output
        assert "openai-yc" in r.output
        e = store.get("openai-yc", Path(runner._config_dir))
        assert e is not None
        assert e.total_tokens == 2_000_000
        assert e.type == EntryType.GRANT

    def test_add_with_expiry(self, runner, tmp_path):
        expires = (date.today() + timedelta(days=180)).isoformat()
        r = invoke(runner, [
            "add", "anthropic-grant",
            "--provider", "anthropic",
            "--type", "grant",
            "--total", "500K",
            "--expires", expires,
            "--label", "Startup program",
        ])
        assert r.exit_code == 0, r.output
        e = store.get("anthropic-grant", Path(runner._config_dir))
        assert e.expires is not None
        assert e.label == "Startup program"

    def test_add_contract_with_monthly_limit(self, runner):
        r = invoke(runner, [
            "add", "openai-capacity",
            "--provider", "openai",
            "--type", "contract",
            "--total", "0",
            "--monthly-limit", "10000000",
        ])
        assert r.exit_code == 0, r.output
        e = store.get("openai-capacity", Path(runner._config_dir))
        assert e.monthly_limit == 10_000_000

    def test_add_k_suffix(self, runner):
        r = invoke(runner, [
            "add", "small-grant",
            "--provider", "cohere",
            "--type", "grant",
            "--total", "250K",
        ])
        assert r.exit_code == 0, r.output
        e = store.get("small-grant", Path(runner._config_dir))
        assert e.total_tokens == 250_000

    def test_add_bad_date(self, runner):
        r = invoke(runner, [
            "add", "bad",
            "--provider", "openai",
            "--type", "grant",
            "--total", "1M",
            "--expires", "not-a-date",
        ])
        assert r.exit_code != 0


class TestStatus:
    def test_status_empty(self, runner):
        r = invoke(runner, ["status"])
        assert r.exit_code == 0
        assert "No entries" in r.output

    def test_status_shows_entries(self, runner):
        invoke(runner, ["add", "openai-yc", "--provider", "openai", "--type", "grant", "--total", "2M"])
        r = invoke(runner, ["status"])
        assert r.exit_code == 0
        assert "openai-yc" in r.output

    def test_status_multiple_providers(self, runner):
        invoke(runner, ["add", "e1", "--provider", "openai", "--type", "grant", "--total", "1M"])
        invoke(runner, ["add", "e2", "--provider", "anthropic", "--type", "grant", "--total", "500K"])
        r = invoke(runner, ["status"])
        assert r.exit_code == 0
        assert "e1" in r.output
        assert "e2" in r.output


class TestUse:
    def test_use_adds(self, runner):
        invoke(runner, ["add", "g", "--provider", "openai", "--type", "grant", "--total", "2M"])
        r = invoke(runner, ["use", "g", "500K"])
        assert r.exit_code == 0
        e = store.get("g", Path(runner._config_dir))
        assert e.used_tokens == 500_000

    def test_use_accumulates(self, runner):
        invoke(runner, ["add", "g", "--provider", "openai", "--type", "grant", "--total", "2M"])
        invoke(runner, ["use", "g", "500K"])
        invoke(runner, ["use", "g", "250K"])
        e = store.get("g", Path(runner._config_dir))
        assert e.used_tokens == 750_000

    def test_use_set_flag(self, runner):
        invoke(runner, ["add", "g", "--provider", "openai", "--type", "grant", "--total", "2M"])
        invoke(runner, ["use", "g", "500K"])
        r = invoke(runner, ["use", "g", "1M", "--set"])
        assert r.exit_code == 0
        e = store.get("g", Path(runner._config_dir))
        assert e.used_tokens == 1_000_000

    def test_use_missing_entry(self, runner):
        r = invoke(runner, ["use", "nonexistent", "100K"])
        assert r.exit_code != 0

    def test_use_m_suffix(self, runner):
        invoke(runner, ["add", "g", "--provider", "openai", "--type", "grant", "--total", "5M"])
        invoke(runner, ["use", "g", "1.5M"])
        e = store.get("g", Path(runner._config_dir))
        assert e.used_tokens == 1_500_000


class TestRemove:
    def test_remove_existing(self, runner):
        invoke(runner, ["add", "g", "--provider", "openai", "--type", "grant", "--total", "1M"])
        r = invoke(runner, ["remove", "g", "--yes"])
        assert r.exit_code == 0
        assert store.get("g", Path(runner._config_dir)) is None

    def test_remove_nonexistent(self, runner):
        r = invoke(runner, ["remove", "ghost", "--yes"])
        assert r.exit_code != 0


class TestEdit:
    def test_edit_label(self, runner):
        invoke(runner, ["add", "g", "--provider", "openai", "--type", "grant", "--total", "1M"])
        r = invoke(runner, ["edit", "g", "--label", "Updated label"])
        assert r.exit_code == 0
        e = store.get("g", Path(runner._config_dir))
        assert e.label == "Updated label"

    def test_edit_total(self, runner):
        invoke(runner, ["add", "g", "--provider", "openai", "--type", "grant", "--total", "1M"])
        r = invoke(runner, ["edit", "g", "--total", "3M"])
        assert r.exit_code == 0
        e = store.get("g", Path(runner._config_dir))
        assert e.total_tokens == 3_000_000

    def test_edit_nonexistent(self, runner):
        r = invoke(runner, ["edit", "ghost", "--label", "x"])
        assert r.exit_code != 0


class TestList:
    def test_list_empty(self, runner):
        r = invoke(runner, ["list"])
        assert r.exit_code == 0
        assert "No entries" in r.output

    def test_list_shows_ids(self, runner):
        invoke(runner, ["add", "a1", "--provider", "openai", "--type", "grant", "--total", "1M"])
        invoke(runner, ["add", "b2", "--provider", "anthropic", "--type", "grant", "--total", "500K"])
        r = invoke(runner, ["list"])
        assert r.exit_code == 0
        assert "a1" in r.output
        assert "b2" in r.output

"""Tests for token_ledger.models."""

from datetime import date, timedelta


from token_ledger.models import Entry, EntryType


def make_entry(**kwargs) -> Entry:
    defaults = dict(
        id="test-grant",
        provider="openai",
        type=EntryType.GRANT,
        total_tokens=2_000_000,
        used_tokens=500_000,
        expires=date.today() + timedelta(days=60),
    )
    defaults.update(kwargs)
    return Entry(**defaults)


class TestEntryComputed:
    def test_remaining_tokens(self):
        e = make_entry(total_tokens=2_000_000, used_tokens=500_000)
        assert e.remaining_tokens == 1_500_000

    def test_remaining_never_negative(self):
        e = make_entry(total_tokens=100, used_tokens=200)
        assert e.remaining_tokens == 0

    def test_pct_used(self):
        e = make_entry(total_tokens=1_000_000, used_tokens=250_000)
        assert e.pct_used == 25.0

    def test_pct_used_zero_total(self):
        e = make_entry(total_tokens=0)
        assert e.pct_used == 0.0

    def test_remaining_unknown_when_total_zero(self):
        e = make_entry(total_tokens=0)
        assert e.remaining_tokens == -1

    def test_days_remaining_future(self):
        e = make_entry(expires=date.today() + timedelta(days=30))
        assert e.days_remaining == 30

    def test_days_remaining_none(self):
        e = make_entry(expires=None)
        assert e.days_remaining is None

    def test_days_remaining_zero_when_today(self):
        e = make_entry(expires=date.today())
        assert e.days_remaining == 0

    def test_is_expired_past(self):
        e = make_entry(expires=date.today() - timedelta(days=1))
        assert e.is_expired is True

    def test_is_expired_future(self):
        e = make_entry(expires=date.today() + timedelta(days=1))
        assert e.is_expired is False

    def test_is_expired_no_expiry(self):
        e = make_entry(expires=None)
        assert e.is_expired is False

    def test_burn_rate(self):
        e = make_entry(used_tokens=300_000)
        rate = e.burn_rate_days(window_days=30)
        assert rate == 10_000.0

    def test_burn_rate_zero_used(self):
        e = make_entry(used_tokens=0)
        assert e.burn_rate_days() == 0.0

    def test_days_until_exhausted(self):
        e = make_entry(total_tokens=1_000_000, used_tokens=0)
        # at 10K/day → 100 days
        assert e.days_until_exhausted(10_000) == 100

    def test_days_until_exhausted_already_empty(self):
        e = make_entry(total_tokens=100, used_tokens=100)
        assert e.days_until_exhausted(1000) == 0

    def test_days_until_exhausted_no_rate(self):
        e = make_entry()
        assert e.days_until_exhausted(0) is None

    def test_days_until_exhausted_unlimited(self):
        e = make_entry(total_tokens=0)
        assert e.days_until_exhausted(10_000) is None


class TestEntrySerialization:
    def test_round_trip(self):
        e = make_entry(label="YC grant", notes="test note")
        d = e.to_dict()
        e2 = Entry.from_dict(d)
        assert e2.id == e.id
        assert e2.provider == e.provider
        assert e2.type == e.type
        assert e2.total_tokens == e.total_tokens
        assert e2.used_tokens == e.used_tokens
        assert e2.expires == e.expires
        assert e2.label == e.label
        assert e2.notes == e.notes

    def test_round_trip_no_expiry(self):
        e = make_entry(expires=None)
        d = e.to_dict()
        e2 = Entry.from_dict(d)
        assert e2.expires is None

    def test_from_dict_defaults(self):
        minimal = {
            "id": "x",
            "provider": "openai",
            "type": "grant",
            "total_tokens": 1000,
        }
        e = Entry.from_dict(minimal)
        assert e.used_tokens == 0
        assert e.label == ""
        assert e.notes == ""
        assert e.expires is None

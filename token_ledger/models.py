"""Data models for token grants and capacity contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional


class EntryType(str, Enum):
    GRANT = "grant"          # Free credits from a provider program (e.g. YC $2M, Anthropic for Startups)
    CONTRACT = "contract"    # Paid capacity contract / reserved throughput (e.g. OpenAI Guaranteed Capacity)
    PREPAID = "prepaid"      # Prepaid credit balance (bought upfront, no expiry pressure)
    SUBSCRIPTION = "subscription"  # Monthly/annual subscription with included tokens


class Provider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"
    COHERE = "cohere"
    OTHER = "other"


@dataclass
class Entry:
    """A single grant, contract, or credit balance."""

    id: str                          # unique slug, e.g. "openai-yc-2026"
    provider: str                    # provider name (free-form for flexibility)
    type: EntryType
    total_tokens: int                # total tokens in the grant/contract (0 = unlimited/unknown)
    used_tokens: int = 0             # tokens consumed so far (manually updated or fetched)
    label: str = ""                  # human label, e.g. "YC S26 batch grant"
    expires: Optional[date] = None   # None = never expires
    monthly_limit: int = 0           # for subscriptions/contracts: tokens per month
    notes: str = ""

    # -- computed helpers --

    @property
    def remaining_tokens(self) -> int:
        if self.total_tokens == 0:
            return -1  # unknown
        return max(0, self.total_tokens - self.used_tokens)

    @property
    def pct_used(self) -> float:
        if self.total_tokens == 0:
            return 0.0
        return self.used_tokens / self.total_tokens * 100

    @property
    def days_remaining(self) -> Optional[int]:
        if self.expires is None:
            return None
        today = date.today()
        delta = (self.expires - today).days
        return max(0, delta)

    @property
    def is_expired(self) -> bool:
        if self.expires is None:
            return False
        return date.today() > self.expires

    def burn_rate_days(self, window_days: int = 30) -> float:
        """Tokens per day based on total used / age of entry (rough heuristic).

        Returns 0 if we can't compute (no used_tokens).
        """
        if self.used_tokens == 0:
            return 0.0
        return self.used_tokens / window_days

    def days_until_exhausted(self, daily_rate: float) -> Optional[int]:
        """Given a daily burn rate, how many days until this entry is exhausted?"""
        if self.total_tokens == 0 or daily_rate <= 0:
            return None
        remaining = self.remaining_tokens
        if remaining <= 0:
            return 0
        return int(remaining / daily_rate)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "provider": self.provider,
            "type": self.type.value,
            "total_tokens": self.total_tokens,
            "used_tokens": self.used_tokens,
            "label": self.label,
            "expires": self.expires.isoformat() if self.expires else None,
            "monthly_limit": self.monthly_limit,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Entry":
        expires = None
        if data.get("expires"):
            expires = date.fromisoformat(data["expires"])
        return cls(
            id=data["id"],
            provider=data["provider"],
            type=EntryType(data["type"]),
            total_tokens=data["total_tokens"],
            used_tokens=data.get("used_tokens", 0),
            label=data.get("label", ""),
            expires=expires,
            monthly_limit=data.get("monthly_limit", 0),
            notes=data.get("notes", ""),
        )

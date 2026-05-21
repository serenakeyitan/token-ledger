# token-ledger

> Startups now manage token grants like equity. `token-ledger` is the cap table for your AI compute.

Track OpenAI Guaranteed Capacity contracts, startup token grants ($2M YC program, Anthropic for Startups, etc.), and prepaid credits — all in one place. Know your burn rate. Know your runway. Never get surprised by an expiring grant.

```
$ token-ledger status

  ID                  Provider     Type      Total    Used    Remaining   Burn    Expires  Runway
 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  anthropic-startup   🟠 anthropic  grant     500K     312K    188K       10.4K/d  45d      18d
  openai-capacity     🟢 openai     contract  ∞        —       ∞          —        334d     —
  openai-yc           🟢 openai     grant     2.0M     847K    1.2M       28.2K/d  194d     42d

  Total remaining: 1.4M  Total used: 1.2M

  ⚠ anthropic-startup expires in 45 days (2026-07-05)
```

## Install

```bash
pip install token-ledger
```

Or from source:

```bash
git clone https://github.com/serenakeyitan/token-ledger
cd token-ledger
pip install -e .
```

## Quickstart

```bash
# Add your YC batch grant
token-ledger add openai-yc \
  --provider openai \
  --type grant \
  --total 2M \
  --expires 2026-12-01 \
  --label "YC S26 batch"

# Add an Anthropic for Startups grant
token-ledger add anthropic-startup \
  --provider anthropic \
  --type grant \
  --total 500K \
  --expires 2026-07-05

# Add an OpenAI Guaranteed Capacity contract (unlimited tokens, monthly limit)
token-ledger add openai-capacity \
  --provider openai \
  --type contract \
  --total 0 \
  --monthly-limit 10M \
  --expires 2027-05-01

# Check status
token-ledger status

# Record usage (after checking your provider dashboard)
token-ledger use openai-yc 250K

# Detailed view of one entry
token-ledger info openai-yc
```

## Commands

| Command | Description |
|---|---|
| `token-ledger status` | Full dashboard — all entries, burn rate, runway |
| `token-ledger add <id>` | Add a grant, contract, or prepaid credit |
| `token-ledger use <id> <tokens>` | Record token usage (additive, or `--set` to override) |
| `token-ledger edit <id>` | Update label, expiry, total, or notes |
| `token-ledger info <id>` | Detailed view of one entry |
| `token-ledger list` | List all entry IDs |
| `token-ledger remove <id>` | Remove an entry |

## Entry types

| Type | When to use |
|---|---|
| `grant` | Free credits from a provider program (YC, Anthropic for Startups, Google for Startups) |
| `contract` | Paid capacity contract with committed throughput (OpenAI Guaranteed Capacity) |
| `prepaid` | Prepaid credit balance you bought upfront |
| `subscription` | Monthly/annual plan with included token allowance |

## Token formats

All token counts accept human-friendly suffixes:

```bash
--total 2M       # 2,000,000
--total 500K     # 500,000
--total 1.5M     # 1,500,000
--total 1000000  # plain integer also works
```

## Burn rate & runway

`token-ledger` computes burn rate as `used_tokens / window_days` (default 30 days). This is a planning heuristic — update your `used_tokens` regularly from your provider dashboards to keep it accurate.

Runway = `remaining_tokens / daily_burn_rate`. Shown in days.

## Data storage

Everything is stored locally in `~/.config/token-ledger/ledger.yaml`. No backend, no telemetry, no auth. The file is human-readable and editable directly if needed.

Override the directory:
```bash
TOKEN_LEDGER_DIR=/path/to/dir token-ledger status
# or
token-ledger --dir /path/to/dir status
```

## Why not just use the provider dashboard?

- You have grants from **multiple providers** with different dashboards
- Provider dashboards show costs, not token counts
- No dashboard shows **expiry + burn rate + runway** in one view
- Guaranteed Capacity contracts don't show token burn at all — only spend
- You want a **local record** independent of provider accounts

## License

Apache 2.0

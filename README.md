# Options Flow Screener

A real-time options flow screener that detects unusual activity using the Tradier API. Built with Python and Rich for a terminal-based dashboard.

## Features

- Real-time options chain scanning across a configurable watchlist
- Unusual activity detection (Vol/OI ratio, large premiums, top 1% volume)
- Interactive filters: calls/puts, ticker, minimum premium, unusual only
- Rich TUI dashboard with summary stats, call/put ratio, and live flow feed
- Sentiment analysis based on bid/ask spread positioning

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Tradier API token
python main.py
```

## Keyboard Controls

| Key | Action |
|-----|--------|
| `c` | Show calls only |
| `p` | Show puts only |
| `a` | Show all (reset filters) |
| `t` | Filter by ticker |
| `m` | Set minimum premium |
| `u` | Toggle unusual only |
| `q` | Quit |

## Configuration

Edit `screener/config.py` to customize:

- `WATCHLIST` — tickers to scan
- `REFRESH_INTERVAL` — seconds between scans
- `VOL_OI_THRESHOLD` — Vol/OI ratio to flag as unusual
- `BIG_PREMIUM_THRESHOLD` — premium threshold for big money alerts
- `USE_SANDBOX` — use sandbox (delayed) or production (real-time) API

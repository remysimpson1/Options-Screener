"""Configuration defaults for the Options Flow Screener."""

WATCHLIST = ["SPY", "QQQ", "AAPL", "TSLA", "NVDA", "AMZN", "META", "MSFT", "AMD", "GOOG"]

REFRESH_INTERVAL = 60          # seconds between scans
VOL_OI_THRESHOLD = 5.0         # volume / open_interest ratio to flag unusual
BIG_PREMIUM_THRESHOLD = 500000 # estimated premium in dollars to flag big money
USE_SANDBOX = False            # True = sandbox (15-min delayed), False = production (real-time)
MAX_EXPIRATIONS = 4            # only scan nearest N expirations per ticker

BASE_URL_PRODUCTION = "https://api.tradier.com/v1"
BASE_URL_SANDBOX = "https://sandbox.tradier.com/v1"

TOP_PERCENT_THRESHOLD = 0.01   # top 1% volume flag
REQUEST_DELAY = 0.12           # seconds between API calls to respect rate limits

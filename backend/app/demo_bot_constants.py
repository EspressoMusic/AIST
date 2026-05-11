"""Paper-only demo bot tuning (not live trading).

Tune thresholds here; imported by risk + bot engine services.
"""

# When True, use relaxed demo thresholds and directional strategy rules.
DEMO_MODE = True

MAX_OPEN_POSITIONS = 2

# Applied while DEMO_MODE is True (paper testing).
DEMO_CONFIDENCE_THRESHOLD = 40.0
DEMO_RISK_SCORE_THRESHOLD = 45.0

# Paper display only: micro-oscillation on top of ExchangeService quotes so open P/L
# updates each tick when the venue price is flat (e.g. dummy fallback). Not execution.
DEMO_TICK_PRICE_JITTER_MAX_FRAC = 0.0006  # ±0.06% of spot per tick, deterministic

# When quantity is zero/missing on a demo trade, use this notional (USD) for P/L math.
DEMO_TRADE_NOTIONAL_USD = 100.0

# Bot-driven Spot Testnet (never mainnet) — conservative caps.
TESTNET_MAX_OPEN_POSITIONS = 1

# Testnet only. No real money. Used to make P/L movement visible during development.
TESTNET_MARKET_BUY_QUOTE_USDT = 1000.0

# Testnet dev visibility only: auto MARKET SELL when any trigger hits (still Spot Testnet REST).
# Thresholds are in **percent points**: +0.10 means +0.10%, not +10%.
TESTNET_DEV_TP_PCT = 0.10
TESTNET_DEV_SL_PCT = -0.10
TESTNET_DEV_MAX_CYCLES_OPEN = 3

ALLOWED_BOT_TESTNET_SYMBOLS = frozenset({"BTCUSDT", "ETHUSDT"})

# --- Spot Testnet strategy engine (entry gating only; exits unchanged) ---
# Klines from Spot Testnet public REST (same venue as orders).
TESTNET_STRATEGY_KLINE_INTERVAL = "15m"
TESTNET_STRATEGY_KLINE_LIMIT = 120
TESTNET_STRATEGY_EMA_FAST = 12
TESTNET_STRATEGY_EMA_SLOW = 26
TESTNET_STRATEGY_RSI_PERIOD = 14
TESTNET_STRATEGY_ATR_PERIOD = 14
# Weighted total must reach this to allow a MARKET BUY.
TESTNET_STRATEGY_MIN_TOTAL_SCORE = 75.0
# Coordinator confidence must meet this (higher after a losing trade on the symbol).
TESTNET_STRATEGY_MIN_CONFIDENCE = 70.0
TESTNET_STRATEGY_MIN_CONFIDENCE_AFTER_LOSS = 80.0
# Risk agent score in this codebase is **higher = safer**; require a solid margin.
TESTNET_STRATEGY_MIN_RISK_SCORE = 60.0
# ATR% = ATR / last close — skip outside this band (too wild or too dead).
TESTNET_STRATEGY_ATR_PCT_MAX = 0.025
TESTNET_STRATEGY_ATR_PCT_MIN = 0.0008
# Cooldown after any close on the same symbol before another BUY.
TESTNET_STRATEGY_COOLDOWN_MINUTES = 10
# Halt new BUYs on a symbol after this many consecutive **losing** closes.
TESTNET_STRATEGY_MAX_CONSECUTIVE_LOSSES = 3
TESTNET_STRATEGY_HALT_HOURS = 2.0

# Stored on DemoTrade.source — surfaced to Flutter /trades.
TRADE_SOURCE_PAPER_DEMO = "PAPER_DEMO"
TRADE_SOURCE_BINANCE_TESTNET = "BINANCE_TESTNET"
TRADE_SOURCE_ALPACA_PAPER = "ALPACA_PAPER"
ALPACA_AI_TEAM_WATCHED_SYMBOLS = ("AAPL", "TSLA", "NVDA", "SPY", "QQQ")
ALPACA_PAPER_DEFAULT_ORDER_USD = 1000.0

# --- Execution gate (non-AI safety; bot engine only) ---
# Kill switch via Settings.bot_kill_switch (env BOT_KILL_SWITCH=true).
# Block new opens when cumulative realized P/L today falls below this (negative USDT).
EXEC_GATE_DAILY_MAX_LOSS_USDT = -500.0
# Max successful opens per UTC calendar day (paper + testnet combined).
EXEC_GATE_MAX_OPENS_PER_DAY = 48
# Minimum seconds between any two successful opens (0 = off).
EXEC_GATE_GLOBAL_OPEN_COOLDOWN_SECONDS = 0

# --- Chief AI demo autonomy (off by default; advisory/safe demo only) ---
CHIEF_DEMO_AUTONOMY_ENABLED_DEFAULT = False
CHIEF_ALLOWED_DEMO_MODES = ("PAPER_DEMO", "BINANCE_TESTNET", "ALPACA_PAPER")

# --- Demo Week Mode safety caps (development/demo only; never live trading) ---
DEMO_WEEK_MODE_DEFAULT = False
DEMO_MAX_DAILY_TRADES = 10
DEMO_MAX_DAILY_LOSS_USDT = 50.0
DEMO_MAX_ORDER_USDT = 1000.0
DEMO_MAX_OPEN_POSITIONS = 1

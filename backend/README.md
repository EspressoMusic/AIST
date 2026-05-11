# Trading Bot API (FastAPI)

Demo backend for the trading bot dashboard. The Flutter app calls **this API only** — no Binance keys in the mobile client.

Planned split:

- **Today**: public **market prices** (read-only) + demo portfolio / bot stubs.
- **Later**: optional Spot **Testnet** trading from this server only (still no keys in Flutter).

## Prerequisites

- Python 3.11+ recommended

## Setup

From the `backend` directory:

```bash
python -m venv .venv
```

**Windows (PowerShell):**

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r app/requirements.txt
```

**macOS / Linux:**

```bash
source .venv/bin/activate
pip install -r app/requirements.txt
```

Optional: copy `.env.example` to `.env`. Trading keys can stay empty — **`GET /market/prices` does not use API keys.**

## Run the server

Inside `backend`, with the virtual environment activated:

```bash
python -m app.run
```

For local development with hot reload:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

Interactive docs are available at `/docs` on whichever host/port you run.

## Production / Cloud Startup

The backend is ready to run behind a cloud HTTPS endpoint. Keep all secrets in
environment variables or your cloud secret manager. Do not put API keys in
Flutter or commit `.env`.

Recommended cloud setup from the `backend` directory:

```bash
pip install -r requirements.txt
python -m app.run
```

Alternative startup command for platforms that inject `PORT`:

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001} --proxy-headers
```

Required/important environment variables:

| Variable | Purpose |
|----------|---------|
| `HOST` | Bind host for `python -m app.run`, default `0.0.0.0`. |
| `PORT` | Bind port for `python -m app.run`, default `8001`. |
| `ENVIRONMENT` | Deployment label shown by `/health`. |
| `DEBUG` | FastAPI debug flag. Keep `false` in production. |
| `CORS_ORIGINS` | Comma-separated Flutter/web origins, or `*` for early demo testing. |
| `CORS_ORIGIN_REGEX` | Optional regex for dynamic preview domains. |
| `USE_BINANCE_TESTNET` | Enables server-side Spot Testnet signed routes only when keys are present. |
| `BINANCE_TESTNET_API_KEY` / `BINANCE_TESTNET_API_SECRET` | Server-only Spot Testnet credentials. Leave empty unless needed. |
| `AI_ADVISOR_PROVIDER` | `MOCK`, `OPENAI`, or `GEMINI`. |
| `OPENAI_API_KEY` / `GEMINI_API_KEY` | Optional AI provider keys, loaded only from environment. |
| `NEWS_PROVIDER` | `MOCK`, `CRYPTOPANIC`, `FINNHUB`, `NEWSAPI`, or `RSS`. |
| `BOT_KILL_SWITCH` | Blocks new opens when `true`. |

Cloud health check:

```bash
curl "$BACKEND_URL/health"
```

Expected shape:

```json
{
  "status": "ok",
  "backend_ok": true,
  "service": "Trading Bot API",
  "environment": "production"
}
```

Use `/system/health` for a fuller operational check. It does not expose secrets.

## Binance Spot Testnet (server-only keys)

Signed REST calls use **Spot Testnet** (`testnet.binance.vision`). **No keys in Flutter.** The **demo bot** still does **not** call these routes — they are manual smoke tests only.

**`backend/.env`** (never commit — already in `.gitignore`):

- `BINANCE_TESTNET_BASE_URL` — default `https://testnet.binance.vision/api`
- `BINANCE_TESTNET_API_KEY` / `BINANCE_TESTNET_API_SECRET` — from [Binance Spot Testnet](https://testnet.binance.vision/)
- `USE_BINANCE_TESTNET=true` — required for signed routes (`/account`, `/balances`, `/test-buy`, `/test-sell`)

**Unsigned** (only needs a reachable testnet host from config):

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/binance-testnet/ping` | Testnet `/v3/ping` |
| `GET` | `/binance-testnet/time` | Server time |

**Signed** (`USE_BINANCE_TESTNET=true` + keys set):

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/binance-testnet/account` | Raw `/v3/account` |
| `GET` | `/binance-testnet/balances` | Non-zero balances |
| `POST` | `/binance-testnet/test-buy` | Testnet **MARKET BUY** (`quoteOrderQty`) |
| `POST` | `/binance-testnet/test-sell` | Testnet **MARKET SELL** (`quantity`) |

Responses include `binance_environment: spot_testnet` and a short **warning** so responses are obviously **not mainnet**.

### Quick curls

Restart the API after editing `.env` so settings reload.

```bash
# Start here — no keys required
curl -s http://127.0.0.1:8000/binance-testnet/ping
curl -s http://127.0.0.1:8000/binance-testnet/time
```

With `.env` flags + keys set:

```bash
curl -s http://127.0.0.1:8000/binance-testnet/account
curl -s http://127.0.0.1:8000/binance-testnet/balances
curl -s -X POST http://127.0.0.1:8000/binance-testnet/test-buy \
  -H "Content-Type: application/json" \
  -d "{\"symbol\":\"BTCUSDT\",\"quote_amount\":11}"
curl -s -X POST http://127.0.0.1:8000/binance-testnet/test-sell \
  -H "Content-Type: application/json" \
  -d "{\"symbol\":\"BTCUSDT\",\"quantity\":0.0001}"
```

Use symbols and sizes allowed by **testnet** filters; rejected orders return HTTP **502** with Binance error JSON in `detail`.

## Market prices (public data only)

`GET /market/prices` tries **live** last-trade prices from Binance **public** REST:

- **Endpoint used** (per symbol):  
  `GET https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT`  
  (and the same for `ETHUSDT`)

- **No API key**, **no signing**, **no orders** — ticker data only.

- **Response shape** (example):

```json
{
  "BTCUSDT": 93156.34,
  "ETHUSDT": 2451.12,
  "source": "binance_public"
}
```

If Binance is unreachable or returns an error, the handler **falls back** to fixed demo numbers and sets:

```json
"source": "fallback_dummy"
```

HTTP timeout per request is **5 seconds** (see `binance_testnet_service.py`).

## Demo bot brain (paper only)

The backend runs a **multi-agent demo pipeline** in memory: news, technical, risk, strategy, learning, decision coordinator, and execution summaries. It reads **live public prices** via `ExchangeService` → `GET /market/prices` logic (Binance public ticker or fallback). **No orders** are sent; positions are **simulated** with simple TP/SL/cycle limits.

- **`POST /bot/start`** — Sets status to **started**, runs **one** decision cycle, returns `{ "status": "started", "message": "Demo bot cycle completed" }`.
- **`POST /bot/stop`** — Sets status to **stopped**, returns `{ "status": "stopped" }`.
- **`POST /bot/tick`** — If started, runs **one** cycle and returns `{ "cycle": { ... } }`. If stopped, returns `{ "status": "stopped", "message": "..." }`.
- **`GET /bot/status`** — `{ "status": "started"|"stopped", "open_trades_count", "history_count", "decisions_count" }`.
- **`GET /trades`** — `{ "open_trades": [...], "history": [...] }` (demo positions).
- **`GET /decisions`** — `{ "decisions": [...] }` newest first.
- **`GET /agents/latest`** — `{ "agents": [...] }` from the last cycle.
- **`GET /lessons`** — `{ "lessons": [...] }` from closed demo trades (newest first).

There is **no background loop**; each cycle runs only when you call **`/bot/start`** or **`/bot/tick`** (or your Flutter auto-tick loop).

### Execution modes (server-side)

- **`PAPER_DEMO`** (default): simulated in-memory trades only — **no Binance orders**.
- **`BINANCE_TESTNET`**: when gates pass, the engine may place **Spot Testnet** MARKET orders (**BTCUSDT** / **ETHUSDT** only, **max one** tracked position, **~10 USDT** quote on BUY). **Not mainnet.** Requires `USE_BINANCE_TESTNET=true` and API keys in **`backend/.env`**.

Endpoints:

- `GET /bot/execution-mode` — current mode.
- `POST /bot/execution-mode` — body `{ "mode": "PAPER_DEMO" | "BINANCE_TESTNET" }` (validates env + keys for Testnet).
- `GET /bot/testnet-orders` — bot-tracked Testnet order attempts/results (debug).
- `GET /bot/status` includes **`execution_mode`**.

Paper portfolio endpoints (`/portfolio`, `/trades`) remain **demo-only**; they do not reflect Binance balances.

## Test endpoints (smoke)

With the server running:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/market/prices
curl http://127.0.0.1:8000/portfolio
curl http://127.0.0.1:8000/trades
curl -X POST http://127.0.0.1:8000/bot/start
curl -X POST http://127.0.0.1:8000/bot/tick
curl http://127.0.0.1:8000/bot/status
curl http://127.0.0.1:8000/decisions
curl http://127.0.0.1:8000/agents/latest
curl http://127.0.0.1:8000/lessons
curl -X POST http://127.0.0.1:8000/bot/stop
```

**Check live vs fallback:** inspect `source` in the `/market/prices` JSON (`binance_public` vs `fallback_dummy`).

**`/trades` example shape:**

```json
{
  "open_trades": [],
  "history": []
}
```

## Safety

- **Demo bot**: simulated positions only; execution agent **never** sends orders.
- **No real money** via this stack until you deliberately add signed trading on **testnet** server-side.
- **Secrets**: API keys belong only in server `.env` (or a secret manager), never in Flutter.

## Flutter

Point HTTP clients at your backend base URL (e.g. `http://10.0.2.2:8000` on Android emulator). Clients may ignore the `source` field on `/market/prices` if they only need prices.

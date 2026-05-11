# PROJECT MAP

## 1) What the app currently does

This Flutter app is a **simulated multi-agent trading dashboard**.

It currently supports:
- Local login/register flow
- Local broker connection setup (paper/demo only)
- Bot settings configuration (risk and strategy limits)
- Pre-flight checks before bot start
- Live fake market prices (BTCUSDT, ETHUSDT)
- Multi-agent decision pipeline (news, technical, risk, strategy, coordinator, execution)
- Automatic fake trade open/close logic
- Live P/L, equity tracking, and chart visualizations
- Activity logs and agent monitoring UI

Everything runs in-app using local state and simulated data.

---

## 2) What is still dummy/local only

The following parts are simulation/local only:
- Authentication storage and session
- Broker connection
- Market data stream
- News analysis
- Technical/risk/strategy outputs
- Trade execution
- Trade history persistence

No external trading systems are called.

---

## 3) Screens that exist and what each does

- `splash_screen.dart`  
  Startup loader while local auth state is checked.

- `login_screen.dart`  
  Email/password login with basic validation.

- `register_screen.dart`  
  Local account creation with validation.

- `main_shell_screen.dart`  
  Main app shell with bottom navigation tabs.

- `dashboard_screen.dart`  
  Main control center:
  - Bot controls (start/stop/emergency)
  - Agents active summary
  - Broker status
  - Live market prices
  - Mini charts
  - Equity curve
  - Key metrics (balance, P/L, open trades)

- `open_trades_screen.dart`  
  Displays currently open simulated trades.

- `trade_history_screen.dart`  
  Displays closed simulated trades.

- `bot_decisions_screen.dart`  
  Shows coordinated decisions and per-agent breakdown.

- `agent_monitor_screen.dart`  
  Live status cards for each agent's latest output.

- `activity_logs_screen.dart`  
  Timeline of bot/system/agent actions with badges and timestamps.

- `settings_screen.dart`  
  Strategy parameters, broker connection section, reset settings, logout.

- `broker_connection_screen.dart`  
  Select/connect dummy broker:
  - Binance Testnet
  - Alpaca Paper Trading
  - Demo Broker

- `preflight_check_screen.dart`  
  Startup checklist before bot can run.

---

## 4) Providers and what each controls

- `auth_provider.dart`  
  Controls local auth/session:
  - init auth state
  - login
  - register
  - logout
  - auth loading/error status

- `broker_provider.dart`  
  Controls local broker state:
  - load saved broker connection
  - connect/disconnect broker
  - expose connection + paper/demo status

- `bot_provider.dart`  
  Core runtime provider:
  - market tick handling
  - bot active/stopped state
  - open/closed trades
  - decisions and agent outputs
  - activity logs
  - settings integration
  - chart data history (rolling 50 points)

---

## 5) Services and what each does

- `auth_storage_service.dart`  
  Saves/loads local user credentials and session (`shared_preferences`).

- `broker_storage_service.dart`  
  Saves/loads local broker connection data.

- `settings_storage_service.dart`  
  Saves/loads bot settings.

- `fake_market_socket_service.dart`  
  Simulates websocket-like price stream for BTC/ETH.

- `dummy_data_service.dart`  
  Provides initial seed data for status/trades/history.

- `preflight_check_service.dart`  
  Builds readiness checklist from provider states.

---

## 6) Agents and what each does

- `news_agent.dart`  
  Simulates news sentiment score (-100 to +100) and explanation.

- `technical_analysis_agent.dart`  
  Simulates trend/momentum/volatility analysis from fake prices.

- `risk_agent.dart`  
  Validates if trade is allowed based on settings and limits.

- `strategy_agent.dart`  
  Combines news + technical + risk result into BUY/SELL/HOLD + confidence.

- `execution_agent.dart`  
  Executes simulated trades only:
  - mark-to-market open trades
  - open new fake trades
  - close by stop loss/take profit/timeout

- `decision_coordinator.dart`  
  Runs all agents in order, builds final coordinated decision, and triggers execution.

---

## 7) Models and what each represents

- `user_model.dart` — local user profile data
- `broker_account_model.dart` — selected broker connection metadata
- `bot_settings_model.dart` — strategy/risk configuration
- `bot_status_model.dart` — current bot status + summary metrics
- `trade_model.dart` — open/closed trade entity
- `activity_log_model.dart` — single log entry
- `chart_point_model.dart` — timestamp/value point for charts
- `preflight_check_model.dart` — checklist item
- `agent_result_model.dart` — result emitted by one agent
- `coordinated_decision_model.dart` — final coordinator decision summary
- `bot_decision_model.dart` — UI-ready rich decision record with agent breakdown

---

## 8) Current user flow

1. **Login/Register**  
   User authenticates locally.

2. **Connect Broker**  
   User connects a dummy paper/demo broker.

3. **Configure Settings**  
   User adjusts risk and strategy limits in Settings.

4. **Pre-flight Check**  
   User taps Start Bot, checklist validates readiness.

5. **Start Bot**  
   Bot begins multi-agent simulated decision loop on market ticks.

6. **Monitor Trades and Decisions**  
   User watches:
   - Dashboard metrics/charts
   - Open trades/history
   - Bot decisions
   - Agent monitor
   - Activity logs

---

## 9) What is NOT implemented yet

- Real backend
- Real broker API integration
- Real money trading
- Real news API
- Push notifications

---

## 10) Recommended next step

Recommended next step: **Introduce a backend contract layer (without real trading yet)**.

Practical plan:
1. Define API contracts (auth, broker, market, decisions, logs) in Dart interfaces.
2. Keep current dummy services as `local` implementations.
3. Add placeholder `remote` implementations with mock HTTP clients.
4. Switch provider dependencies through a simple environment config.

This keeps current behavior stable but prepares the project for real integrations with minimal refactor later.

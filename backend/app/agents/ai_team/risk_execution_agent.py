"""Risk & Execution Agent."""

from __future__ import annotations

from app.agents.ai_team.base_agent import AgentResponse, AiTeamContext, BaseAiTeamAgent


class RiskExecutionAgent(BaseAiTeamAgent):
    agent_name = "Risk & Execution Agent"
    role = "Protect the account and approve/block trades."

    def analyze(self, context: AiTeamContext) -> AgentResponse:
        snap = dict(context.risk_snapshot or {})
        if not snap:
            return self.response(
                action="HOLD",
                confidence=0.0,
                risk_level="HIGH",
                veto=True,
                short_reason="Risk data unavailable",
                reason="Risk snapshot was missing, so the safest advisory response is HOLD.",
                data_used={"current_status": "MOCK"},
                current_status="MOCK",
                trade_allowed=False,
                position_size=0.0,
                risk_checks={"data_available": False},
            )

        checks = self._build_checks(snap)
        failed = [name for name, row in checks.items() if row.get("veto") is True]
        vetoes = [str(checks[name].get("reason") or name) for name in failed]
        risk_points = 0.0
        for row in checks.values():
            risk_points += float(row.get("risk_points") or 0.0)

        veto = bool(vetoes)
        trade_allowed = not veto
        suggested_position = self._safe_position_size(snap, risk_points, trade_allowed)
        if veto:
            action = "HOLD"
            confidence = min(92.0, 58.0 + risk_points)
            risk_level = "HIGH" if risk_points >= 45 else "MEDIUM"
            short_reason = "Trade blocked by safety checks"
            reason = " ".join(vetoes)
        else:
            action = "HOLD"
            confidence = max(54.0, 78.0 - risk_points)
            risk_level = "LOW" if risk_points < 15 else "MEDIUM"
            short_reason = "Trade allowed by risk checks"
            reason = (
                "All current real internal safety checks passed. This agent only approves "
                "or blocks future decisions and does not execute trades."
            )

        return self.response(
            action=action,
            confidence=confidence,
            risk_level=risk_level,  # type: ignore[arg-type]
            veto=veto,
            short_reason=short_reason,
            reason=reason,
            data_used={
                "current_status": "REAL_DATA",
                "trade_allowed": trade_allowed,
                "position_size": suggested_position,
                "open_trades": snap.get("open_trades", []),
                "closed_trades_count": snap.get("closed_trades_count"),
                "portfolio": snap.get("portfolio", {}),
                "realized_pnl": snap.get("realized_pnl"),
                "unrealized_pnl": snap.get("unrealized_pnl"),
                "daily_loss": snap.get("daily_loss"),
                "trade_count_today": snap.get("trade_count_today"),
                "consecutive_losses": snap.get("consecutive_losses"),
                "current_open_position_count": snap.get("current_open_position_count"),
                "kill_switch_active": snap.get("kill_switch_active"),
                "cooldown_active": snap.get("cooldown_active"),
                "cooldown_reason": snap.get("cooldown_reason"),
                "execution_mode": snap.get("execution_mode"),
                "risk_points": round(risk_points, 2),
                "checked_rules": [
                    "kill switch",
                    "max one open position",
                    "exposure check",
                    "daily loss check",
                    "trade count limit",
                    "consecutive losses",
                    "cooldown after loss",
                    "safe position size",
                    "final execution approval",
                ],
                "risk_checks": checks,
            },
            current_status="REAL_DATA",
            trade_allowed=trade_allowed,
            position_size=suggested_position,
            risk_checks=checks,
        )

    def _build_checks(self, snap: dict[str, object]) -> dict[str, dict[str, object]]:
        kill = bool(snap.get("kill_switch_active"))
        open_count = int(snap.get("current_open_position_count") or 0)
        daily_loss = float(snap.get("daily_loss") or 0.0)
        daily_loss_limit = float(snap.get("daily_loss_limit") or -500.0)
        trade_count = int(snap.get("trade_count_today") or 0)
        trade_limit = int(snap.get("daily_trade_limit") or 0)
        consecutive_losses = int(snap.get("consecutive_losses") or 0)
        max_losses = int(snap.get("max_consecutive_losses") or 3)
        cooldown = bool(snap.get("cooldown_active"))

        return {
            "kill_switch": {
                "passed": not kill,
                "veto": kill,
                "reason": "Kill switch is active." if kill else "Kill switch is off.",
                "risk_points": 100 if kill else 0,
            },
            "max_one_open_position": {
                "passed": open_count == 0,
                "veto": open_count >= 1,
                "reason": (
                    "There is already an open position."
                    if open_count >= 1
                    else "No open position is currently blocking a new trade."
                ),
                "risk_points": 40 if open_count >= 1 else 0,
            },
            "daily_loss_limit": {
                "passed": daily_loss > daily_loss_limit,
                "veto": daily_loss <= daily_loss_limit,
                "reason": (
                    f"Daily realized P/L {daily_loss:.2f} reached limit {daily_loss_limit:.2f}."
                    if daily_loss <= daily_loss_limit
                    else f"Daily realized P/L {daily_loss:.2f} is above limit {daily_loss_limit:.2f}."
                ),
                "risk_points": 35 if daily_loss <= daily_loss_limit else 0,
            },
            "daily_trade_limit": {
                "passed": trade_count < trade_limit,
                "veto": trade_count >= trade_limit,
                "reason": (
                    f"Daily trade count {trade_count}/{trade_limit} reached."
                    if trade_count >= trade_limit
                    else f"Daily trade count {trade_count}/{trade_limit} is available."
                ),
                "risk_points": 25 if trade_count >= trade_limit else 0,
            },
            "consecutive_losses": {
                "passed": consecutive_losses < max_losses,
                "veto": consecutive_losses >= max_losses,
                "reason": (
                    f"Consecutive losses {consecutive_losses}/{max_losses} reached."
                    if consecutive_losses >= max_losses
                    else f"Consecutive losses {consecutive_losses}/{max_losses} are below limit."
                ),
                "risk_points": min(35, consecutive_losses * 10),
            },
            "cooldown": {
                "passed": not cooldown,
                "veto": cooldown,
                "reason": str(snap.get("cooldown_reason") or "No cooldown is active."),
                "risk_points": 30 if cooldown else 0,
            },
        }

    def _safe_position_size(
        self,
        snap: dict[str, object],
        risk_points: float,
        trade_allowed: bool,
    ) -> float:
        if not trade_allowed:
            return 0.0
        base = float(snap.get("suggested_position_size_default") or 100.0)
        drawdown = float(snap.get("drawdown_proxy") or 0.0)
        multiplier = 1.0
        if risk_points >= 20:
            multiplier *= 0.75
        if drawdown < 0:
            multiplier *= 0.85
        return round(max(25.0, min(base, base * multiplier)), 2)

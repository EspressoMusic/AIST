from typing import Any

from fastapi import APIRouter, Depends

from app.deps import get_ai_provider_service
from app.models.bot_api_model import TeamChatReply, TeamChatRequest, TeamChatResponse
from app.services.ai_provider_service import AIProviderService

router = APIRouter(prefix="/ai-advisor", tags=["ai-advisor"])

_TEAM_PERSONAS = [
    {
        "id": "trades",
        "name": "סוכן עסקאות",
        "role": "בודק פוזיציות, כניסה/יציאה וניהול עסקה.",
        "prompt": "Focus on trade execution context, open position logic, and whether action is practical.",
    },
    {
        "id": "news",
        "name": "סוכן חדשות",
        "role": "בודק חדשות, סנטימנט וכותרות שיכולות להשפיע על השוק.",
        "prompt": "Focus on news, macro sentiment, crypto headlines, and what should be watched next.",
    },
    {
        "id": "technical",
        "name": "סוכן אנליסטים",
        "role": "בודק גרף, EMA, RSI, ATR, מומנטום ותמיכה/התנגדות.",
        "prompt": "Focus on technical analysis and chart conditions. Mention indicators to verify.",
    },
    {
        "id": "risk",
        "name": "סוכן סיכון",
        "role": "בודק חשיפה, הפסדים, תנודתיות, ווטו ובטיחות.",
        "prompt": "Focus on risk, downside, exposure, position sizing, and whether to veto.",
    },
    {
        "id": "learning",
        "name": "סוכן למידה",
        "role": "לומד מהעסקאות האחרונות ומהטעויות שחוזרות על עצמן.",
        "prompt": "Focus on lessons from recent trades, what to improve, and repeated mistakes.",
    },
    {
        "id": "ai",
        "name": "סוכן AI",
        "role": "מסכם חשיבה רחבה ומחבר בין כל הסוכנים.",
        "prompt": "Focus on a balanced AI synthesis. Be concise and practical.",
    },
    {
        "id": "debate",
        "name": "מנהל הדיון",
        "role": "משווה בין הדעות ומציע מסקנה צוותית.",
        "prompt": "Focus on disagreements between agents and produce a team-level conclusion.",
    },
]


@router.get("/status")
def ai_advisor_status(
    service: AIProviderService = Depends(get_ai_provider_service),
) -> dict[str, Any]:
    return service.status()


@router.post("/team-chat", response_model=TeamChatResponse)
def team_chat(
    request: TeamChatRequest,
    service: AIProviderService = Depends(get_ai_provider_service),
) -> TeamChatResponse:
    """Ask all trading agents for an opinion. Advisory only, never execution."""
    user_message = request.message.strip()
    replies: list[TeamChatReply] = []
    for persona in _TEAM_PERSONAS:
        advice = service.analyze_with_ai(
            (
                "Team chat inside the trading bot app. "
                "Answer in Hebrew as this exact agent. "
                "You are recommendation-only and cannot execute trades. "
                f"Agent name: {persona['name']}. Role: {persona['role']}. "
                f"Guidance: {persona['prompt']} "
                "Put the agent's direct short Hebrew answer in short_reason, "
                "and a slightly fuller Hebrew explanation in reason. "
                "If the user asks for a trade, still answer as advice only. "
                f"User message: {user_message}"
            ),
            None,
        )
        replies.append(
            TeamChatReply(
                agent_id=persona["id"],
                agent_name=persona["name"],
                role=persona["role"],
                answer=str(advice.get("short_reason") or advice.get("reason") or "אין תשובה."),
                detail=str(advice.get("reason") or ""),
                action=str(advice.get("action") or "HOLD").upper(),  # type: ignore[arg-type]
                confidence=float(advice.get("confidence") or 0.0),
                risk_level=str(advice.get("risk_level") or "MEDIUM").upper(),  # type: ignore[arg-type]
                veto=bool(advice.get("veto")),
            ),
        )
    return TeamChatResponse(
        user_message=user_message,
        provider_status=service.status(),
        replies=replies,
    )

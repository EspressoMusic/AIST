"""Production-friendly app runner.

Cloud platforms can run either:
- `python -m app.run`
- `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

This module reads host/port from environment-backed Settings and does not load
or print secrets.
"""

from __future__ import annotations

import uvicorn

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()

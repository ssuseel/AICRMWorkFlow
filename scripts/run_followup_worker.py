"""Persistent follow-up worker entry point.

Run on a scheduler or managed worker:
python scripts/run_followup_worker.py
"""

import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


def run_once() -> int:
    from src.config.settings import get_settings
    from src.db.session import SessionLocal
    from src.services.follow_up_service import FollowUpService

    settings = get_settings()
    with SessionLocal() as session:
        count = FollowUpService(
            session,
            str(settings.default_tenant_id),
        ).mark_overdue()
    print(f"Marked {count} follow-up(s) overdue")
    return count


if __name__ == "__main__":
    run_once()

"""Retry due CRM synchronization records once.

Run this command from a persistent scheduler or managed worker:
python scripts/run_crm_sync_worker.py
"""

import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.config.settings import get_settings
from src.db.session import SessionLocal
from src.services.crm_service import CRMService


def run_once() -> int:
    settings = get_settings()
    with SessionLocal() as session:
        service = CRMService(
            session,
            str(settings.default_tenant_id),
        )
        count = service.retry_due()
    print(f"Processed {count} due CRM synchronization(s)")
    return count


if __name__ == "__main__":
    run_once()

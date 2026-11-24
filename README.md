# AICRMWorkFlow

AI-powered customer workflow platform for lead capture, qualification, approved email outreach, response classification, follow-ups, CRM synchronization and analytics.

## Project status

Phase 4 email drafting and mock sending are implemented.

Architecture documents:

- [Architecture](docs/ARCHITECTURE.md)
- [Database schema](docs/DATABASE_SCHEMA.md)
- [API contracts](docs/API_CONTRACTS.md)
- [Workflow states](docs/WORKFLOW_STATES.md)
- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)
- [Testing strategy](docs/TESTING_STRATEGY.md)

## Local setup

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m sample_data.seed_demo
streamlit run app.py
```

The default database is SQLite for local demonstration. Set `DATABASE_URL` to a PostgreSQL URL for production-style execution.

## Database migrations

```bash
alembic upgrade head
alembic downgrade base
```

## Tests

```bash
pytest -q
ruff check .
```

External AI, email and CRM integrations default to mock-safe configuration. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` for local Streamlit secrets.

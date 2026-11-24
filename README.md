# AICRMWorkFlow

AI-powered customer workflow platform for lead capture, qualification, approved email outreach, response classification, follow-ups, CRM synchronization and analytics.

## Project status

Phase 8 adds mock CRM synchronization and a Salesforce REST adapter.

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

To configure Salesforce, set `CRM_PROVIDER=salesforce` and provide `SALESFORCE_CLIENT_ID`, `SALESFORCE_CLIENT_SECRET`, and `SALESFORCE_LOGIN_URL` through environment variables or Streamlit secrets. Configure a Salesforce Connected App for OAuth client-credentials flow. Credentials are not persisted in the database. Leave `CRM_PROVIDER=mock` for demonstration mode.

Salesforce task/activity idempotency uses the `AICRM_Idempotency_Key__c` custom Task field. Create that field in Salesforce before enabling task/activity creation. The CRM synchronization UI supports tenant-specific local-to-remote lead field overrides.

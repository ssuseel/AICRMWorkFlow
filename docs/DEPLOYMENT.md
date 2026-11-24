# Streamlit Community Cloud Deployment

## Requirements

- Push this repository to a GitHub repository accessible by the Streamlit
  Community Cloud account.
- Provision a reachable PostgreSQL database for persistent shared data.
- Python 3.11 or newer. Dependencies are declared in `requirements.txt`.

SQLite is suitable for local development and disposable smoke checks only.
Streamlit Community Cloud instances can restart, so SQLite data is not a
persistent production database.

## Deploy

1. In Streamlit Community Cloud, create an app from the repository and select
   the intended branch.
2. Set the main file path to `app.py`.
3. Configure the database and provider settings in the app's **Secrets** panel.
   Do not commit credentials or a `.streamlit/secrets.toml` file.
4. Deploy and wait for the app health check. The default AI, email, and CRM
   providers remain mock-safe.

Example Community Cloud secrets:

```toml
DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require"
APP_ENV = "production"
LOG_LEVEL = "INFO"
DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"
AI_PROVIDER = "mock"
EMAIL_PROVIDER = "mock"
CRM_PROVIDER = "mock"
SEED_DEMO_DATA = true
```

Replace the example database URL with the provider's SSL-enabled connection
string. Keep the password in the Cloud Secrets panel, not in source control.
Demo seeding is enabled if `SEED_DEMO_DATA` is omitted; it creates fictional
leads and is idempotent. Set it to `true` only for an isolated demo workspace,
and explicitly set it to `false` for a workspace that uses real customer data.

## Schema and Demo Data

Before deploying an updated schema, run migrations using a trusted release
environment with the same `DATABASE_URL`:

```bash
alembic upgrade head
```

The app also ensures missing tables exist at startup for a fresh demo database.
That is not a replacement for applying migrations to an existing production
database.

For local development:

```bash
python -m sample_data.seed_demo
```

## Provider Configuration

- Start with `AI_PROVIDER = "mock"`, `EMAIL_PROVIDER = "mock"`, and
  `CRM_PROVIDER = "mock"`.
- Gmail requires the Gmail OAuth values in `.streamlit/secrets.toml.example`.
- Salesforce requires Connected App client-credentials configuration and
  `SALESFORCE_CLIENT_ID` / `SALESFORCE_CLIENT_SECRET`.
- Do not enable external sending or CRM synchronization until provider
  credentials, scopes, suppression rules, and the approval workflow are
  validated for the target tenant.

## Verification

GitHub Actions runs lint, formatting, unit tests, migration upgrade/downgrade,
and a seeded-database deployment smoke check on pushes and pull requests.
For local verification:

```bash
ruff check .
ruff format --check .
pytest -q
DATABASE_URL=sqlite:////tmp/aicrm-deploy.db alembic upgrade head
DATABASE_URL=sqlite:////tmp/aicrm-deploy.db python -m sample_data.seed_demo
DATABASE_URL=sqlite:////tmp/aicrm-deploy.db python -m scripts.deployment_smoke
```

## Operational Limitations

This repository does not provision PostgreSQL, configure a Streamlit Cloud
account, or perform a cloud deployment automatically. User authentication,
role-based authorization, production tenant onboarding, backup/restore, and
live-provider integration verification must be completed before handling real
customer data.

# Architecture

## 1. Goals

AICRMWorkFlow is a modular monolith for managing lead capture through CRM synchronization and analytics. It starts with a Streamlit UI and is structured so FastAPI endpoints, background workers and external integrations can be added without rewriting business logic.

## 2. System Layers

- **Presentation:** Streamlit pages and reusable UI components.
- **API:** FastAPI application for future/internal integration (not the initial UI).
- **Application services:** Workflow, lead, qualification, email, response, follow-up, CRM and analytics orchestration.
- **Domain:** Pydantic models, enums, workflow transition rules and scoring rules.
- **Repository layer:** SQLAlchemy sessions and tenant-scoped database operations.
- **Infrastructure:** PostgreSQL, Alembic, logging, configuration, AI/email/CRM provider adapters.
- **Workers:** Persistent follow-up and synchronization jobs. Scheduled execution must not depend on Streamlit reruns.

## 3. Module Layout

```text
app.py
src/
  config/
  db/
  domain/
  repositories/
  services/
  integrations/
    ai/
    email/
    crm/
  api/
  ui/
prompts/
alembic/
tests/
docs/
sample_data/
.streamlit/
```

## 4. Key Components

### Lead lifecycle

`LeadService` validates, deduplicates, creates, updates and assigns leads. Lead data is always tenant-scoped. Repository queries enforce tenant isolation.

### Qualification

`LeadQualificationService` requests structured evidence from an AI provider, validates it with Pydantic and applies deterministic weighted scoring in Python. AI output cannot change persisted workflow state or execute CRM operations directly.

### Email

`EmailService` manages generated drafts, edits, approval and sending. Only a human-approved draft may reach `EmailProvider.send()`. The mock provider is the default.

### Responses

`ResponseService` ingests email-provider messages, validates classified content and proposes follow-up actions. Initial release processing is advisory and never sends an automatic response.

### Follow-ups

`FollowUpService` creates, reschedules and completes persistent tasks using deterministic business-day rules. An external scheduler or worker polls due tasks.

### CRM

`CRMService` applies field mappings and idempotency keys, and delegates external operations to CRM adapters. AI output is never a direct instruction to a CRM.

### Analytics

Analytics services execute database aggregation queries. Dashboard values are never hardcoded in production UI code.

## 5. Dependencies

- Python 3.11
- Streamlit
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- PostgreSQL driver
- OpenAI-compatible provider SDK behind a provider interface
- pytest, pytest-cov
- ruff
- python-dotenv or environment/Streamlit configuration

## 6. Provider Interfaces

### AI

```text
AIProvider.qualify(prompt, context) -> QualificationEvidence
AIProvider.generate_email(prompt, context) -> EmailDraftOutput
AIProvider.classify_response(prompt, context) -> ResponseClassificationOutput
```

### Email

```text
EmailProvider.send(message) -> DeliveryResult
EmailProvider.fetch_incoming(since) -> list[IncomingMessage]
EmailProvider.get_thread(thread_id) -> EmailThread
```

Adapters: mock (default), Gmail, Outlook.

### CRM

```text
CRMProvider.upsert_lead(lead, mapping) -> SyncResult
CRMProvider.upsert_contact(contact, mapping) -> SyncResult
CRMProvider.associate_account(...)
CRMProvider.create_task(...)
CRMProvider.log_activity(...)
```

Adapters: mock (default), Salesforce, HubSpot, Zoho.

## 7. Configuration

Configuration is loaded from environment variables and Streamlit secrets. Secrets are never committed. A provider is selected through configuration. Development uses SQLite only for fast local tests; production uses PostgreSQL. PostgreSQL-specific constraints and migrations remain in Alembic.

## 8. Security and Isolation

- Every tenant-owned entity has `tenant_id`.
- Repository operations require tenant context.
- RBAC is enforced in services and API dependencies.
- CSV values and email content are treated as untrusted input.
- Prompt templates are separated from runtime customer data and protected from direct execution or disclosure.
- API keys, OAuth refresh tokens and database credentials are externalized.
- Audit records capture actor, action, entity, before/after state and timestamps without secrets.

## 9. Reliability

- External operations use an idempotency key and audit record.
- Retries use bounded exponential backoff.
- Transient provider failures are retried; permanent failures stop and expose an error.
- Email sending requires an approved, immutable approved-content snapshot.
- Duplicate records are prevented by database constraints and service checks.
- Follow-up and CRM jobs use persistent pending work; browser reruns are not schedulers.

## 10. Observability

Structured logging records timestamp, tenant ID, module, event, model/prompt version, operation status and correlation ID. Secrets and unnecessary personal data are excluded.

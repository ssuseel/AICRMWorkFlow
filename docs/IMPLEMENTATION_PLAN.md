# Implementation Plan

## Phase 0 - Architecture and Planning

Status: complete.

Deliverables:

- Architecture and module boundaries
- Database schema
- API contracts
- Workflow transitions
- Testing strategy
- Dependency and risk register

## Phase 1 - Application Foundation

Status: complete.

- Create Streamlit entry point and navigation
- Add configuration and logging
- Add SQLAlchemy base, engine/session management and tenant context
- Add Alembic and initial migration
- Add Pydantic domain schemas
- Add repository/service package structure
- Add sample data and seed command
- Build enterprise dashboard from database metrics
- Add baseline unit and smoke tests

Exit criteria: app launches locally; demo data loads; dashboard executes real aggregate queries; database migrations run.

## Phase 2 - Lead Management

Status: complete.

- Implement lead model and repositories
- Implement validated create/update/delete/assignment/status operations
- Add normalized email duplicate detection
- Add CSV import with per-row errors
- Build paginated search/filter/sort UI
- Add lead detail/edit views
- Add tenant isolation tests

Exit criteria: lead CRUD/import/filter operations persist and pass focused tests.

## Phase 3 - AI Qualification

- Add AI provider abstraction and fallback
- Store qualification and email prompts under `prompts/`
- Add Pydantic structured-output schemas
- Implement deterministic weighted score
- Store evidence, missing information and recommendation history
- Add qualification UI
- Mock provider in tests

Exit criteria: AI provider output is validated; unavailable provider falls back safely; score follows testable rules.

## Phase 4 - Email Generation

- Add email template and draft models
- Implement AI draft generation
- Add draft edit/save/preview/approval UI
- Persist approved content snapshot
- Implement mock email provider
- Enforce human approval

Exit criteria: users can generate/edit/approve drafts; sending denied before approval.

## Phase 5 - Email Integration

- Implement Gmail and Outlook adapters behind the email interface
- Add OAuth configuration and secure secret handling
- Implement send, retrieval and thread lookup
- Add delivery event and bounce handling
- Add retry policies

Exit criteria: mock mode works; real adapters are inactive unless configured; failure handling is tested.

## Phase 6 - Response Intelligence

- Add incoming response ingestion
- Implement Pydantic response classifier
- Store summaries and classification metadata
- Cancel follow-ups on reply/unsubscribe
- Add human review queue

Exit criteria: classifications are persisted and cancellation behavior is deterministic; no automatic send.

## Phase 7 - Follow-up Management

- Implement follow-up model/service
- Add configurable business rules
- Implement business-day calculation
- Add due/overdue UI and history
- Add persistent worker/scheduler entry point
- Add cancellation rules

Exit criteria: due work survives reruns; reply/unsubscribe cancels tasks; schedule tests pass.

## Phase 8 - CRM Integration

- Implement CRM provider abstraction
- Add mock and provider-specific adapters
- Add field mapping and idempotent sync records
- Implement retries and error reporting
- Add external sync UI

Exit criteria: mock synchronization works; real adapters only operate with valid credentials; retries pass tests.

## Phase 9 - Analytics

- Implement aggregation services
- Build acquisition, qualification, email, follow-up, pipeline and CRM health views
- Add global filters
- Verify all metrics against database fixtures

Exit criteria: analytics are database-driven and match test fixtures.

## Phase 10 - Quality and Testing

- Run unit, integration and UI smoke tests
- Add GitHub Actions for lint/type/test
- Review security and tenant isolation
- Resolve defects before phase signoff

## Phase 11 - Deployment

- Add `app.py`, requirements, environment/secrets examples
- Add Streamlit configuration
- Add deployment documentation
- Add smoke/deployment workflow
- Verify demo launch

## Dependencies and Sequence

1. Foundation and database precede all domain modules.
2. Lead and lead repository precede qualification and email.
3. Email drafting precedes send integration.
4. Response ingestion requires email/thread identity.
5. Follow-ups require lead and response services.
6. CRM integration follows stable lead and workflow models.
7. Analytics is last because it depends on all persisted events.

## Security and Compliance

- Secret isolation
- Tenant isolation
- RBAC
- Suppression/unsubscribe enforcement
- Prompt-injection boundaries
- PII minimization and audit logs
- OAuth least privilege

## Major Risks

1. Streamlit Community Cloud and PostgreSQL networking/configuration.
2. SQLite-to-PostgreSQL differences in JSON and constraints.
3. OAuth token lifecycle and provider changes.
4. AI structured-output instability.
5. Duplicate detection across CSV normalization and provider imports.
6. Scheduler reliability outside Streamlit.
7. Scope growth across CRM and email providers.
8. Human approval enforcement across UI and API paths.

## Mitigations

- SQLAlchemy/Albian cross-database design and PostgreSQL CI.
- Strict Pydantic schemas and fallback provider.
- Centralized normalization and database uniqueness.
- APScheduler or external worker with persistent queue in a later phase.
- Initial mock adapters and feature configuration.
- Approval snapshots and centralized sending service.

# Testing Strategy

Phase 5 coverage includes Gmail send mapping, incoming message decoding, thread retrieval, provider selection, and missing Gmail credential rejection.

Phase 6 coverage includes response classification, response deduplication, lead engagement, and unsubscribe follow-up cancellation.

Phase 7 coverage includes business-day calculations, scheduling, rescheduling, completion, cancellation, overdue transitions, and persistent worker execution.

Phase 8 coverage includes tenant-scoped mock synchronization, idempotency, audit events, transient retry scheduling, permanent failures, field mapping, Salesforce OAuth configuration, lead create/update-by-email, and task idempotency. Provider tests use fake HTTP responses and do not call Salesforce.

Phase 9 coverage validates date, owner, industry and source filtering; database-backed lead acquisition, qualification, conversion, email, follow-up, pipeline, CRM health and team metrics; empty data; and tenant isolation.

Phase 10 CI gates run Ruff lint and format checks, the complete pytest suite, and an Alembic upgrade/downgrade migration check.

Phase 4 coverage includes draft creation and preview, draft edits, approval snapshots, approval enforcement, mock delivery, and idempotency-key persistence.

Phase 2 coverage includes lead duplicate handling, lead updates and assignment, CSV imports, soft deletion safeguards, repository filtering, and tenant isolation.

## Test levels

- **Unit:** deterministic domain, validation, workflow, scoring and scheduling behavior.
- **Repository:** tenant-scoped SQL queries and constraints.
- **Service:** lead, email, follow-up and CRM orchestration with mocked providers.
- **Integration:** migrations, PostgreSQL behavior and provider adapters using mocks or local emulators.
- **UI smoke:** Streamlit app launch and representative page interactions.
- **Security:** tenant isolation and permission checks.

## Required test areas

### Foundation

- configuration validation
- database session lifecycle
- migrations upgrade/downgrade
- audit event creation

### Leads

- valid and invalid manual capture
- normalized duplicate detection
- CSV import success/duplicate/rejected counts
- edit/delete safeguards
- owner/status changes
- filter combinations, sorting and pagination
- tenant isolation

### AI

- Pydantic-valid structured output
- invalid provider output
- fallback behavior
- deterministic weighted score
- evidence/missing information handling
- prompt-version metadata

### Email

- draft creation/edit/save
- approval permissions
- approved snapshot creation
- send denied without approval
- idempotent sending
- mock delivery and failure events

### Workflow

- all valid transitions
- rejection of invalid transitions
- audit and workflow event creation

### Follow-ups

- business-day calculation
- due/overdue transition
- rescheduling
- completion
- cancellation on reply/unsubscribe
- persistence independent of Streamlit reruns

### CRM

- lead/contact upsert
- account association
- task/activity creation
- duplicate external IDs
- transient retry and permanent failure
- field mapping

### Analytics

- fixture-based acquisition, qualification, email, follow-up and CRM metrics
- filter correctness
- empty dataset behavior

## External mocks

Tests never use live AI, Gmail, Outlook, Salesforce, HubSpot or Zoho services. Mock adapters implement success, timeout, permanent error and duplicate scenarios.

## Quality gates

- pytest passes
- ruff passes
- type checks pass once configured
- no high-severity dependency or secrets findings
- Alembic upgrade succeeds from an empty database
- Streamlit smoke launch succeeds
- GitHub Actions required check passes

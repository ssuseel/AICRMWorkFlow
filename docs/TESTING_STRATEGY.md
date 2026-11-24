# Testing Strategy

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

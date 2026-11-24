# API Contracts

The initial release exposes domain operations through application services and Streamlit. FastAPI routes below are the target contract for future/internal API exposure.

## Common rules

- JSON request/response bodies
- Authentication required for all mutating routes
- Tenant inferred from authenticated context; not accepted as a user field
- Pydantic request and response validation
- `X-Correlation-ID` supported and propagated to audit events
- Standard error shape:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable summary",
    "details": []
  }
}
```

## Leads

### `POST /api/v1/leads`

Creates a lead. Email is normalized and duplicate leads return `409 LEAD_DUPLICATE`.

```json
{
  "first_name": "Asha",
  "last_name": "Patel",
  "email": "asha@example.com",
  "company": "Example",
  "title": "VP Operations",
  "industry": "Manufacturing",
  "source": "CSV",
  "owner_id": "uuid"
}
```

### `GET /api/v1/leads`

Supports `q`, `source`, `industry`, `company`, `owner_id`, `status`, `min_score`, `max_score`, `created_from`, `created_to`, `next_follow_up_from`, `next_follow_up_to`, `sort`, `page`, `page_size`.

### `GET /api/v1/leads/{lead_id}`

### `PATCH /api/v1/leads/{lead_id}`

Partial update with immutable ID and tenant fields.

### `DELETE /api/v1/leads/{lead_id}`

Soft delete unless protected by active approved/sent communications or open CRM synchronization. Conflict response: `409 LEAD_DELETE_RESTRICTED`.

### `POST /api/v1/leads/import`

Accepts CSV content or a persistent upload reference. Returns counts for created, duplicate and rejected rows.

## Qualification

### `POST /api/v1/leads/{lead_id}/qualify`

Returns:

```json
{
  "lead_id": "uuid",
  "score": 82,
  "customer_intent": "High",
  "summary": "Evidence-based summary",
  "evidence": {},
  "missing_information": [],
  "recommended_actions": [],
  "model_name": "provider-model",
  "prompt_version": "qualification-v1",
  "status": "QUALIFIED"
}
```

## Email

### `POST /api/v1/leads/{lead_id}/emails`

Creates an editable draft.

### `PATCH /api/v1/emails/{email_id}`

Updates draft fields only while in `DRAFT`.

### `POST /api/v1/emails/{email_id}/submit-for-approval`

### `POST /api/v1/emails/{email_id}/approve`

Requires `EMAIL_APPROVE` permission. Captures an immutable approval snapshot.

### `POST /api/v1/emails/{email_id}/send`

Requires `EMAIL_SEND` permission and human approval. `Idempotency-Key` is mandatory.

## Responses

### `POST /api/v1/email-responses`

Provider callback or worker ingestion payload. Never directly sends a response.

### `GET /api/v1/email-responses/{response_id}`

## Follow-ups

### `POST /api/v1/leads/{lead_id}/follow-ups`

### `PATCH /api/v1/follow-ups/{follow_up_id}`

Supports reschedule and completion.

### `POST /api/v1/follow-ups/{follow_up_id}/cancel`

## CRM

### `POST /api/v1/leads/{lead_id}/crm-sync`

Creates an idempotent sync request.

### `GET /api/v1/crm-sync/{sync_id}`

## Analytics

### `GET /api/v1/analytics/summary`

### `GET /api/v1/analytics/acquisition`

### `GET /api/v1/analytics/qualification`

### `GET /api/v1/analytics/emails`

### `GET /api/v1/analytics/follow-ups`

### `GET /api/v1/analytics/crm-health`

All analytics endpoints accept date, owner, industry, source and status filters.

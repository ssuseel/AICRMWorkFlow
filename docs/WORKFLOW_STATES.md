# Workflow States and Transitions

All state changes are persisted and append `workflow_events` and `audit_events` records. Invalid transitions are rejected in the application service and database boundary.

## Lead

States:

- `NEW`
- `VALIDATED`
- `QUALIFICATION_PENDING`
- `QUALIFIED`
- `DISQUALIFIED`
- `CONTACTED`
- `ENGAGED`
- `CUSTOMER`
- `SUPPRESSED`
- `DELETED`

Transitions:

- `NEW -> VALIDATED`
- `NEW -> SUPPRESSED`
- `VALIDATED -> QUALIFICATION_PENDING`
- `QUALIFICATION_PENDING -> QUALIFIED`
- `QUALIFICATION_PENDING -> DISQUALIFIED`
- `QUALIFIED -> CONTACTED`
- `CONTACTED -> ENGAGED`
- `ENGAGED -> CUSTOMER`
- `ENGAGED -> DISQUALIFIED`
- `VALIDATED/QUALIFIED/CONTACTED/ENGAGED -> SUPPRESSED`
- `NEW/VALIDATED/QUALIFIED/DISQUALIFIED -> DELETED` (soft delete with safeguards)

Lead reassignment does not change lead workflow state.

## Email

States:

- `DRAFT`
- `PENDING_APPROVAL`
- `APPROVED`
- `SCHEDULED`
- `SENDING`
- `SENT`
- `DELIVERY_FAILED`
- `BOUNCED`
- `CANCELLED`

Transitions:

- `DRAFT -> PENDING_APPROVAL`
- `PENDING_APPROVAL -> DRAFT`
- `PENDING_APPROVAL -> APPROVED`
- `APPROVED -> SCHEDULED`
- `APPROVED -> CANCELLED`
- `SCHEDULED -> SENDING`
- `SCHEDULED -> CANCELLED`
- `SENDING -> SENT`
- `SENDING -> DELIVERY_FAILED`
- `SENT -> BOUNCED`
- `DELIVERY_FAILED -> SENDING` only for an approved retry

A sender snapshot of subject/body/recipient is captured at approval. External send requires `APPROVED` or explicit retry policy.

## Follow-up

States:

- `OPEN`
- `SCHEDULED`
- `OVERDUE`
- `COMPLETED`
- `CANCELLED`

Transitions:

- `OPEN -> SCHEDULED`
- `OPEN -> CANCELLED`
- `SCHEDULED -> OVERDUE`
- `SCHEDULED -> COMPLETED`
- `OVERDUE -> COMPLETED`
- `SCHEDULED/OVERDUE -> CANCELLED`

Customer reply or unsubscribe cancels active follow-ups with a recorded reason.

## CRM Sync

States:

- `PENDING`
- `IN_PROGRESS`
- `SYNCED`
- `RETRY_SCHEDULED`
- `PERMANENT_FAILURE`

Transitions:

- `PENDING -> IN_PROGRESS`
- `IN_PROGRESS -> SYNCED`
- `IN_PROGRESS -> RETRY_SCHEDULED`
- `RETRY_SCHEDULED -> IN_PROGRESS`
- `RETRY_SCHEDULED -> PERMANENT_FAILURE`
- `IN_PROGRESS -> PERMANENT_FAILURE`

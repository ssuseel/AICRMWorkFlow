# Database Schema

## Conventions

- Primary keys: UUID.
- All tenant-owned tables include `tenant_id` and foreign-key tenant isolation context.
- Timestamps: `created_at`, `updated_at` with UTC values.
- Soft delete is preferred for leads and emails when audit/history is required.
- Database constraints supplement service-level validation.

## Tables

### tenants

- `id` UUID primary key
- `name`
- `slug` unique
- `status`
- `settings` JSONB
- timestamps

### users

- `id` UUID primary key
- `tenant_id` FK tenants
- `email`
- `display_name`
- `role`
- `status`
- timestamps

Unique: (`tenant_id`, `email`)

### leads

- `id` UUID primary key
- `tenant_id`
- `first_name`
- `last_name`
- `email`
- `phone`
- `company`
- `title`
- `industry`
- `source`
- `status`
- `owner_id` FK users
- `qualification_score` integer
- `qualification_status`
- `next_follow_up_at`
- `deleted_at`
- `created_by_id`
- timestamps

Unique: (`tenant_id`, normalized email) where email is not null
Indexes: tenant/status, tenant/owner, tenant/source, tenant/industry, tenant/created_at, tenant/next_follow_up_at

### lead_custom_fields

- `id`
- `tenant_id`
- `lead_id`
- `key`
- `value`

Unique: (`lead_id`, `key`)

### lead_qualification

- `id`
- `tenant_id`
- `lead_id`
- `model_name`
- `prompt_version`
- `status`
- `score`
- `business_requirements` JSONB
- `customer_intent`
- `product_interest` JSONB
- `budget_assessment`
- `timeline_assessment`
- `authority_assessment`
- `evidence` JSONB
- `missing_information` JSONB
- `recommended_actions` JSONB
- timestamps

Unique: latest is determined by most recent `created_at`; multiple history records are retained.

### email_templates

- `id`
- `tenant_id`
- `name`
- `category`
- `subject_template`
- `body_template`
- `approved`
- `version`
- timestamps

### emails

- `id`
- `tenant_id`
- `lead_id`
- `template_id`
- `subject`
- `body`
- `status`
- `approval_status`
- `approved_by_id`
- `approved_at`
- `approved_subject`
- `approved_body`
- `provider`
- `provider_message_id`
- `thread_id`
- `idempotency_key`
- `sent_at`
- timestamps

Unique: (`tenant_id`, `idempotency_key`) where key is not null
Index: tenant/status

### email_events

- `id`
- `tenant_id`
- `email_id`
- `event_type`
- `provider_event_id`
- `occurred_at`
- `payload` JSONB
- timestamps

Unique: (`tenant_id`, `provider_event_id`) where provider event ID is not null

### email_responses

- `id`
- `tenant_id`
- `lead_id`
- `email_id`
- `provider_message_id`
- `thread_id`
- `from_address`
- `classification`
- `summary`
- `customer_intent`
- `recommended_action`
- `priority`
- `human_review_required`
- `unsubscribed`
- `raw_content` JSONB
- timestamps

Unique: (`tenant_id`, `provider_message_id`)

### follow_ups

- `id`
- `tenant_id`
- `lead_id`
- `owner_id`
- `title`
- `description`
- `priority`
- `status`
- `scheduled_at`
- `due_at`
- `completed_at`
- `cancelled_at`
- `cancellation_reason`
- timestamps

Indexes: tenant/status/due_at, tenant/owner/status

### crm_connections

- `id`
- `tenant_id`
- `provider`
- `status`
- `configuration` JSONB
- `credentials_ref`
- timestamps

Credentials are external secrets references, never stored plaintext.

### crm_mappings

- `id`
- `tenant_id`
- `provider`
- `local_field`
- `remote_field`
- timestamps

Unique: (`tenant_id`, `provider`, `local_field`)

### crm_sync_records

- `id`
- `tenant_id`
- `lead_id`
- `connection_id`
- `provider`
- `external_id`
- `entity_type`
- `status`
- `attempt_count`
- `next_retry_at`
- `last_error`
- `idempotency_key`
- timestamps

Unique: (`tenant_id`, `idempotency_key`)

### audit_events

- `id`
- `tenant_id`
- `actor_id`
- `entity_type`
- `entity_id`
- `action`
- `before_state` JSONB
- `after_state` JSONB
- `correlation_id`
- timestamps

Index: tenant/entity, tenant/created_at

### workflow_events

- `id`
- `tenant_id`
- `entity_type`
- `entity_id`
- `from_state`
- `to_state`
- `actor_id`
- `reason`
- timestamps

Index: tenant/entity/entity_id/created_at

# Analytics Definitions

All analytics queries require a tenant ID and exclude soft-deleted leads.
Date filtering applies to each section's measurement date: lead creation for
acquisition, qualification, conversion and pipeline; email creation for email
performance; follow-up creation for follow-up effectiveness; and sync-record
creation for CRM health. Owner, industry, source and status filters are applied
to the associated lead's current attributes.

## Metrics

- **Lead acquisition:** count of leads grouped by UTC creation date.
- **Qualification distribution:** lead counts by score bands `0-39`, `40-69`,
  and `70-100`.
- **Lead-to-customer conversion:** current customer leads divided by all leads
  in the filtered lead cohort.
- **Email delivery rate:** emails in `SENT` divided by terminal delivery
  attempts (`SENT`, `BOUNCED`, or `DELIVERY_FAILED`).
- **Email response rate:** distinct persisted responses associated with an
  email divided by sent emails. It may exceed one response per email but uses
  distinct response records.
- **Follow-up completion:** completed follow-ups divided by all follow-ups in
  the filtered follow-up cohort. Overdue count is reported separately.
- **Follow-up conversions:** distinct customer leads with a completed
  follow-up.
- **Pipeline activity:** current lead counts grouped by workflow status.
- **CRM health:** persisted sync attempts grouped by sync status.
- **Team productivity:** per-owner lead, qualified/customer, and sent-email
  counts; unassigned leads are reported separately.

These are operational metrics, not financial forecasts. CRM, email, and
qualification results reflect records currently persisted in the application.

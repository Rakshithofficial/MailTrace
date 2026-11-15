# MailTrace Database Design

**Primary target:** PostgreSQL  
**Early-development fallback:** SQLite with the same logical model and migrations kept portable where practical.

## 1. Design Rules

- Use UUID primary keys for domain entities.
- Store UTC timestamps.
- Keep raw email content in controlled storage or a protected file reference, not in logs.
- Store evidence and normalized indicators separately so relationships can be reused across cases.
- Do not store uploaded attachment bytes in a form that can be executed. Preserve metadata and hashes; optionally store quarantined bytes with strict access controls.

## 2. Entities and Fields

### `investigation_cases`

- `id` UUID, primary key
- `title` text, required
- `status` text, required: `RECEIVED`, `PARSING`, `ANALYZING`, `REVIEW`, `CLOSED`, `FAILED`
- `risk_score` integer, 0-100
- `severity` text: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
- `verdict` text: `BENIGN`, `SUSPICIOUS`, `MALICIOUS`, `INCONCLUSIVE`
- `summary` text nullable
- `analyst_note` text nullable
- `created_at`, `updated_at` timestamps, required

### `emails`

- `id` UUID, primary key
- `case_id` UUID, foreign key to `investigation_cases.id`, unique for MVP
- `message_id` text nullable
- `subject` text nullable
- `sender` text nullable
- `recipients` JSON/text array
- `cc` JSON/text array
- `reply_to` text nullable
- `sent_at` timestamp nullable
- `body_text` text nullable
- `body_html` text nullable
- `received_headers` JSON/text array
- `authentication_results` JSON/text array
- `urls` JSON array of inert extracted URL metadata
- `attachments` JSON array of inert attachment metadata and SHA-256 hashes
- `raw_content_reference` text, required
- `raw_sha256` text, required
- `created_at` timestamp, required

### `header_evidence`

- `id` UUID, primary key
- `email_id` UUID, foreign key to `emails.id`
- `header_name` text, required
- `value` text, required
- `parsed_value` JSON nullable
- `finding_id` UUID, nullable foreign key to `findings.id`

### `indicators`

- `id` UUID, primary key
- `type` text, required: `IP`, `DOMAIN`, `URL`, `HASH`, `EMAIL`, `ASN`
- `value` text, required
- `normalized_value` text, required
- `source` text, required
- `confidence` numeric, 0-1
- `first_seen`, `last_seen` timestamps, required

A unique constraint on (`type`, `normalized_value`) prevents duplicate canonical indicators.

### `case_indicators`

- `case_id` UUID, foreign key to `investigation_cases.id`
- `indicator_id` UUID, foreign key to `indicators.id`
- `location` text nullable, such as `header`, `body`, or `attachment`
- `evidence_reference` text nullable
- Primary key: (`case_id`, `indicator_id`)

### `findings`

- `id` UUID, primary key
- `case_id` UUID, foreign key to `investigation_cases.id`
- `category` text, required
- `rule_id` text, required
- `title` text, required
- `description` text, required
- `severity` text, required
- `score_contribution` integer, required
- `confidence` numeric, 0-1
- `created_at` timestamp, required

### `finding_evidence`

- `id` UUID, primary key
- `finding_id` UUID, foreign key to `findings.id`
- `evidence_type` text, required
- `value` text, required
- `location` text nullable
- `metadata` JSON nullable

### `relationships`

- `id` UUID, primary key
- `source_indicator_id` UUID, foreign key to `indicators.id`
- `target_indicator_id` UUID, foreign key to `indicators.id`
- `source_case_id` UUID, nullable foreign key to `investigation_cases.id`
- `target_case_id` UUID, nullable foreign key to `investigation_cases.id`
- `relationship_type` text, required
- `confidence` numeric, 0-1
- `strength` text: `STRONG`, `MEDIUM`, `WEAK`
- `evidence` JSON/text, required
- `created_at` timestamp, required

### `campaigns`

- `id` UUID, primary key
- `name` text, required
- `confidence` numeric, 0-1
- `first_seen`, `last_seen` timestamps
- `created_at` timestamp

### `campaign_cases`

- `campaign_id` UUID, foreign key to `campaigns.id`
- `case_id` UUID, foreign key to `investigation_cases.id`
- Primary key: (`campaign_id`, `case_id`)

### `recommendations`

- `id` UUID, primary key
- `case_id` UUID, foreign key to `investigation_cases.id`
- `action` text, required
- `reason` text, required
- `priority` text: `LOW`, `MEDIUM`, `HIGH`
- `evidence_reference` JSON nullable
- `created_at` timestamp

### `analysis_runs`

- `id` UUID, primary key
- `case_id` UUID, foreign key to `investigation_cases.id`
- `analyzer_version` text, required
- `status` text, required
- `result` JSON, required; includes normalized approximate infrastructure context such as source IPs, DNS context, ASN/ISP data, geolocation observations, and limitations
- `created_at`, `completed_at` timestamps

### `reports`

- `id` UUID, primary key
- `case_id` UUID, foreign key to `investigation_cases.id`
- `format` text, required
- `content_reference` text, required
- `generated_at` timestamp, required

## 3. Relationships

- One `investigation_case` has one MVP `email`, many `findings`, `recommendations`, `analysis_runs`, and `reports`.
- One `email` has many `header_evidence` records.
- Cases and indicators are many-to-many through `case_indicators`.
- Findings have many evidence records.
- Relationships connect indicators; related cases emerge through shared indicators.
- Campaigns contain many cases through `campaign_cases`.

Foreign keys use restrictive deletion by default. Deleting a case must be an explicit retention operation that also handles dependent evidence.

## 4. Useful Indexes

- `investigation_cases(status, created_at DESC)`
- `investigation_cases(severity, created_at DESC)`
- `emails(message_id)`
- `indicators(type, normalized_value)` unique
- `case_indicators(indicator_id, case_id)`
- `findings(case_id, severity)`
- `finding_evidence(finding_id)`
- `relationships(source_indicator_id)` and `relationships(target_indicator_id)`
- `analysis_runs(case_id, created_at DESC)`
- `campaign_cases(case_id)`

## 5. Example Records

```text
investigation_cases
id: 11111111-1111-1111-1111-111111111111
status: REVIEW
risk_score: 81
severity: CRITICAL
verdict: SUSPICIOUS

emails
id: 22222222-2222-2222-2222-222222222222
case_id: 11111111-1111-1111-1111-111111111111
sender: billing@example.test
raw_sha256: 7a9d...

indicators
id: 33333333-3333-3333-3333-333333333333
type: DOMAIN
value: Example-Login.TEST
normalized_value: example-login.test
source: email_body
confidence: 0.95

findings
id: 44444444-4444-4444-4444-444444444444
case_id: 11111111-1111-1111-1111-111111111111
rule_id: URL-002
title: Look-alike domain
severity: HIGH
score_contribution: 20
```

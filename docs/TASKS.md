# MailTrace Phased Build Plan

Tasks are intentionally small, independently testable, and suitable for one AI-assisted implementation at a time. Each task should include a human review and focused tests before the next task begins.

## Phase 0: Blueprint and Contracts

- **P0-T01** Confirm repository structure and record technology choices. Test: structure review against `BLUEPRINT.md`.
- **P0-T02** Freeze API resource names and schemas. Test: example request/response validation review.
- **P0-T03** Define database entities, constraints, and migrations plan. Test: schema review for keys and relationships.
- **P0-T04** Define deterministic threat-rule IDs and initial weights. Test: each rule has evidence and score behavior.
- **P0-T05** Prepare synthetic sample-data manifest. Test: every sample category has an expected outcome.
- **P0-T06** Create a safety checklist for uploads, URLs, secrets, and external services. Test: checklist review.

## Phase 1: Email Intake

- **P1-T01** Create the FastAPI application health endpoint. Test: `GET /health` returns a stable schema.
- **P1-T02** Add case creation with pasted RFC 5322 content. Test: valid and invalid payloads.
- **P1-T03** Add controlled `.eml` upload validation and size limits. Test: accepted, oversized, and unsupported files.
- **P1-T04** Parse MIME messages with a mature parser. Test: headers, text body, HTML body, and multipart fixtures.
- **P1-T05** Persist cases and parsed email metadata. Test: create then retrieve a case.
- **P1-T06** Return safe errors with request IDs. Test: malformed input has no stack trace or secret.

## Phase 2: Local Analysis

- **P2-T01** Extract and normalize sender, recipients, reply-to, and message ID. Test: address fixtures.
- **P2-T02** Parse Received and authentication-result headers, including source-IP candidates. Test: known SPF/DKIM/DMARC and routing examples.
- **P2-T03** Extract URLs without making network requests. Test: obfuscated and plain URL fixtures.
- **P2-T04** Normalize domains with a public-suffix-aware library. Test: case, trailing dot, IDN, and subdomain cases.
- **P2-T05** Record attachment metadata and SHA-256 hashes without execution. Test: known hashes and MIME mismatches.
- **P2-T06** Implement sender, header, auth, URL, domain, attachment, and content rules. Test: one focused fixture per rule.

## Phase 3: Risk and Findings

- **P3-T01** Persist findings and structured evidence. Test: finding round trip.
- **P3-T02** Implement de-duplicated weighted scoring and severity ranges. Test: boundary scores 0, 24, 25, 49, 50, 74, 75, 100.
- **P3-T03** Store versioned analysis runs. Test: repeat analysis preserves prior run.
- **P3-T04** Add recommendations from evidence-backed templates. Test: malicious URL and attachment scenarios.
- **P3-T05** Produce explanation-ready JSON. Test: schema validation and no raw secrets.

## Phase 4: Optional Threat Intelligence

- **P4-T01** Define the internal threat-intelligence provider interface. Test: local provider contract.
- **P4-T02** Implement a no-network local provider. Test: deterministic fixture responses.
- **P4-T03** Add one approved external provider behind configuration. Test: mocked success, rate limit, timeout, and unavailable states.
- **P4-T04** Normalize provider results and label source/confidence. Test: provider response mapping.
- **P4-T05** Ensure provider failure leaves local analysis usable. Test: analysis succeeds with provider disabled/failing.

## Phase 5: Relationships and Campaigns

- **P5-T01** Persist canonical indicators and case links. Test: duplicate normalization merges indicators.
- **P5-T02** Match strong relationships by shared domain, URL, IP, or attachment hash. Test: two campaign fixtures connect.
- **P5-T03** Add medium/weak relationship evidence using infrastructure or content similarity. Test: confidence and strength labels.
- **P5-T04** Return possible campaign groups with cautious wording. Test: unrelated cases do not form a group.
- **P5-T05** Add a simple relationship API response. Test: graph payload contains nodes and edges.

## Phase 6: Explanation Layer

- **P6-T01** Define an explanation-provider interface. Test: deterministic fallback provider.
- **P6-T02** Add an existing hosted or local model adapter without making it authoritative. Test: mocked structured response.
- **P6-T03** Add timeout, unavailable, and malformed-response fallback handling. Test: all failure modes return template explanation.
- **P6-T04** Label model output and preserve source findings. Test: explanation cannot alter score or evidence.

## Phase 7: Report and Demo Polish

- **P7-T01** Generate a report from stored case data. Test: report works with enrichment and AI disabled.
- **P7-T02** Add fixed end-to-end synthetic demo fixtures. Test: upload through report.
- **P7-T03** Review safety, limitations, and approximate-location wording. Test: manual release checklist.
- **P7-T04** Prepare the five-minute demonstration and backup path. Test: demo rehearsal offline.

## Working Agreement

Implement one task at a time. Keep pull requests small, review generated code, add a focused test, and update the relevant contract when behavior changes. Do not start frontend polish or infrastructure expansion before the MVP path is stable.

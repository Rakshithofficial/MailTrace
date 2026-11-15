# SIH26106 — Email Threat Investigation & Intelligence Workbench
## Master Project Blueprint
**Version:** 1.0 — Planning Only

## 1. Product Goal
A web-based security investigation platform for SIH26106 that goes beyond the question **“Is this phishing?”**. The platform should accept a controlled `.eml` file (preferred) or pasted email content, extract evidence, analyze suspicious elements, enrich available infrastructure information, connect related emails, calculate an explainable risk assessment, provide response guidance, and preserve the result as a case/report.

**Product story:** Detect → Explain → Correlate → Investigate → Respond.

## 2. Team Constraints
- Only 2–3 members are expected to handle most coding.
- Heavy use of Copilot/Claude/Cursor/local coding models is allowed.
- **No custom LLM training.**
- **No autonomous AI agents or multi-agent orchestration.**
- Prefer mature libraries, deterministic rules, existing APIs, pretrained models, and conventional software engineering.
- Every external AI/API dependency needs a fallback.

## 3. Final Five Outcomes
### 1. Complete Email Threat Investigation
One unified case view combining sender details, headers, authentication indicators, URLs, attachments, content signals, enrichment results, and a clear evidence-backed assessment.

### 2. Malicious Element Detection & Localization
Identify/highlight suspicious URLs, look-alike domains, sender anomalies, risky attachments, QR codes where supported, and social-engineering patterns. Show the exact evidence that triggered findings.

### 3. Origin & Infrastructure Intelligence
Extract available source IPs, domains, DNS context, ASN/ISP information, and approximate geolocation. **Never claim exact attacker identity or physical location.**

### 4. Threat Relationship & Campaign Intelligence
Connect cases through shared domains, URLs, IPs, attachment hashes and content similarity. Display a graph and group related cases into a **possible campaign** with confidence wording.

### 5. Explainable Risk Assessment & Response Recommendation
Combine evidence into a transparent 0–100 risk score, show score contributors, explain the result, and recommend practical defensive actions such as quarantine, block, search related mail, review users, or preserve evidence.

**Report generation is an output layer over these five outcomes, not a separate core capability.**

## 4. User Journey
1. Dashboard → New Investigation.
2. Upload `.eml` or paste email.
3. Parse message.
4. Analyze headers, sender, URLs, domains, attachments and content.
5. Optionally enrich indicators using approved threat-intelligence services.
6. Compare with stored cases.
7. Show campaign/relationship graph.
8. Calculate risk.
9. Use an existing LLM/local model to explain findings and recommendations.
10. Save case and export report.

## 5. Core Architecture
```text
USER
  ↓
Email Intake (.eml / paste)
  ↓
Parser
  ↓
┌──────────────┬───────────────┬──────────────┐
Headers      URLs/Domains    Attachments   Content
  └──────────────┬───────────────┴──────────────┘
                 ↓
          Local Analysis Layer
                 ↓
       Optional Threat Intelligence
                 ↓
          Indicator Store
                 ↓
       Relationship / Campaign Layer
                 ↓
              Risk Engine
                 ↓
        Existing LLM Explanation
                 ↓
         Case + Recommendations
                 ↓
             Report Output
```

## 6. Technology Direction
**Frontend:** React + TypeScript + Vite (unless the strongest coder has a better-known conventional stack).

**Backend:** Python + FastAPI preferred; Node/Express acceptable if already familiar.

**Database:** PostgreSQL for the fuller build; SQLite acceptable for early MVP.

**Email:** mature `.eml`/MIME parser.

**Threat intelligence:** optional adapters for services such as VirusTotal/urlscan.io or other approved sources.

**AI:** existing hosted LLM or existing local model through Ollama/compatible runtime. The LLM is an explanation/summarization layer, not the sole detector.

## 7. Repository Structure
```text
mailtrace/
├── apps/
│   ├── web/
│   │   └── src/
│   │       ├── components/
│   │       ├── pages/
│   │       ├── features/
│   │       └── lib/
│   └── api/
│       └── app/
│           ├── api/
│           ├── services/
│           ├── analyzers/
│           ├── models/
│           ├── schemas/
│           ├── integrations/
│           └── core/
├── packages/            # optional if needed
├── sample_data/
│   ├── benign/
│   ├── phishing/
│   ├── spoofing/
│   └── campaign/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/
│   ├── BLUEPRINT.md
│   ├── API.md
│   ├── DATABASE.md
│   ├── THREAT_RULES.md
│   ├── TASKS.md
│   └── DEMO.md
├── .env.example
└── README.md
```

## 8. Core Data Model
**InvestigationCase:** id, created_at, status, risk_score, severity, verdict, summary.

**Email:** id, case_id, message_id, subject, sender, recipients, reply_to, date, raw_content_reference.

**HeaderEvidence:** id, email_id, header_name, value, parsed_value, finding.

**Indicator:** id, type, value, normalized_value, source, confidence, created_at. Types: IP, DOMAIN, URL, HASH, EMAIL, ASN.

**Finding:** id, case_id, category, title, description, severity, score_contribution, evidence_reference.

**Relationship:** id, source_indicator_id, target_indicator_id, relationship_type, confidence.

**Campaign:** id, name, confidence, first_seen, last_seen.

**Recommendation:** id, case_id, action, reason, priority.

## 9. Risk Engine — Start Simple
Use weighted evidence first; do not train a complex model.

Example starting weights:
- Sender anomaly +15
- Domain impersonation +20
- Malicious URL +25
- Header/auth anomaly +15
- Suspicious attachment +10
- Social-engineering indicators +10
- Threat-intelligence hit +20

Normalize to 0–100. Example severity defaults: 0–24 LOW, 25–49 MEDIUM, 50–74 HIGH, 75–100 CRITICAL. Tune later against the test set.

Every score contribution must be traceable to evidence.

## 10. Threat Relationship / Campaign Logic
Start with simple, deterministic relationships:
- **Strong:** same normalized domain, URL, IP, attachment hash.
- **Medium:** same sender infrastructure, strong content similarity, similar URL path patterns.
- **Weak:** general wording similarity.

Do not start with graph ML. Use relational data + simple similarity + a graph visualization library. Advanced clustering is optional only after MVP stability.

## 11. AI / LLM Role
Use existing models to:
- explain findings
- summarize a case
- classify intent as a supporting signal
- summarize campaign context
- convert technical findings into analyst-readable language
- generate response recommendations
- assist with report wording

Do not use an LLM as the only authority for phishing verdicts, malicious URLs, infrastructure location, attacker identity, or forensic evidence.

Prefer structured input such as:
```json
{
  "risk_score": 91,
  "findings": [
    {"title":"Domain impersonation","severity":"high","evidence":"example-login.com"},
    {"title":"Suspicious URL","severity":"critical","evidence":"https://..."}
  ]
}
```

## 12. Threat-Intelligence Integration
Hide vendors behind adapters:
```text
ThreatIntelProvider
├── VirusTotalProvider
├── UrlscanProvider
└── LocalProvider
```

Normalize responses into an internal format. API failure must not break the investigation.

## 13. Minimum Viable Product
MVP is complete when the team can:
1. Upload a controlled `.eml`.
2. Parse and display it.
3. Extract headers and URLs.
4. Normalize domains.
5. Run basic sender/header/auth checks.
6. Hash attachments and flag basic suspicious types/metadata.
7. Produce a transparent risk score.
8. Show suspicious elements.
9. Store the case.
10. Connect at least two related test emails.
11. Display a simple relationship graph.
12. Produce an LLM explanation OR fallback template.
13. Export a clean investigation report.

## 14. Development Phases
### Phase 0 — Blueprint
Docs, API contracts, data model, rules, sample-data plan.

### Phase 1 — Email Intake
`.eml` upload, parsing, rendering, case creation.

### Phase 2 — Local Analysis
Headers, sender, auth results, URLs, domains, attachments, hashing.

### Phase 3 — Risk Engine
Findings, weights, score, severity, explanation-ready JSON.

### Phase 4 — Threat Intelligence
Provider adapters, keys/configuration, quotas, graceful failures.

### Phase 5 — Relationship Intelligence
Indicator storage, related-case search, relationship graph, possible campaign grouping.

### Phase 6 — AI Explanation
Existing model integration, structured prompts, fallback output.

### Phase 7 — Report + Demo Polish
Timeline, report export, dashboard polish, fixed test cases, presentation flow.

## 15. Team Split
- **Member 1:** backend/parser — ingestion, parsing, APIs, case lifecycle.
- **Member 2:** frontend/dashboard — investigation UI, email highlighting, risk views.
- **Member 3:** security analysis — headers, URLs, domains, attachments, rules/scoring.
- **Member 4:** threat graph/data — relationships, similarity, campaign view.
- **Member 5:** AI/integrations — LLM adapter, prompts, enrichment adapters.
- **Member 6:** testing/documentation — sample emails, evaluation set, reports, demo.

If only 2–3 people actually code, the other roles become QA, documentation, test-data creation, UI support and demo preparation rather than independent engineering tracks.

## 16. Sample Data
Use controlled/synthetic data during development. Suggested folders:
```text
sample_data/
├── benign/
├── phishing/
├── spoofing/
└── campaign/
```
Campaign samples should deliberately share some indicators so the relationship graph has a meaningful demonstration.

## 17. Testing
Unit-test parsing, URL extraction, domain normalization, header checks, hashing and scoring.

Integration-test upload → parse → analyze, analyze → save case, save → relationship matching, case → report.

Maintain fixed known-good demo emails. The final demo must not depend on live services.

## 18. Safety / Reliability Boundaries
Never:
- execute uploaded attachments
- run macros
- automatically open suspicious URLs
- send sensitive real-world emails to third parties without authorization
- claim exact attacker identity or physical location
- promise perfect phishing detection

Use synthetic data, safe static analysis, redacted logs and optional external enrichment.

## 19. AI Coding Rule
AI coding tools should implement **one small, testable task at a time**. Do not ask an AI tool to build the whole application in one pass.

Every generated change should be reviewed, tested and kept consistent with this blueprint.

## 20. Definition of Done
A feature is done only when:
- code works
- errors are handled
- tests exist where meaningful
- data is persisted when needed
- documentation is updated
- sample data exercises it
- fallback behavior is known

## 21. Final Product Statement
**MailTrace is an AI-assisted email threat investigation platform that goes beyond phishing classification by exposing malicious elements, analyzing available infrastructure, connecting related threats into possible campaigns, providing evidence-backed risk assessment, and guiding defensive response.**

The implementation deliberately uses existing tools, pretrained models, APIs, deterministic analysis and conventional engineering instead of custom LLM training or autonomous AI agents.

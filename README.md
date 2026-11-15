# MailTrace

MailTrace is the SIH26106 AI-Powered Email Threat Detection, Geolocation & Forensic Intelligence Platform: an AI-assisted email threat investigation and intelligence workbench. It accepts controlled `.eml` files or pasted email content, extracts evidence, analyzes available sender and infrastructure context with approximate geolocation where supported, applies deterministic analysis, connects related cases, calculates an explainable risk assessment, and produces response guidance and reports.

## Architecture

MailTrace uses a modular monolith:

```text
React + TypeScript + Vite
          |
FastAPI modular backend
          |
Parser -> local analyzers/rules -> indicator store
          |                         |
optional enrichment             relationships/campaigns
          |                         |
          risk engine -> explanation adapter -> case/report
          |
PostgreSQL (SQLite during early development)
```

The local parser and rule engine remain functional without external services. Optional threat-intelligence adapters and an existing hosted/local model provide enrichment and explanation only. The LLM is never the primary security detector or the authority for a verdict, exact origin, attacker identity, or physical location.

## Prerequisites

- Git
- Python 3.11+ and a virtual environment
- Node.js 20+ and npm
- PostgreSQL for the fuller build, or SQLite for early development
- Optional: credentials for an approved threat-intelligence provider
- Optional: an existing hosted LLM or local compatible runtime such as Ollama

No external service or model is required for the deterministic MVP and offline demo.

## Development Phases

1. **Phase 0:** contracts, data model, threat rules, and safe synthetic fixtures
2. **Phase 1:** `.eml` intake, parsing, case creation, and persistence
3. **Phase 2:** local header, sender, URL, domain, attachment, and content analysis
4. **Phase 3:** findings, explainable scoring, recommendations, and versioned analysis
5. **Phase 4:** optional threat-intelligence adapters with graceful failure
6. **Phase 5:** indicator relationships, related cases, and possible campaigns
7. **Phase 6:** existing-model explanation with deterministic fallback
8. **Phase 7:** reports, fixed demo fixtures, testing, and presentation polish

See [docs/TASKS.md](docs/TASKS.md) for independently testable task IDs.

## Important Safety Rules

- Never execute uploaded attachments, macros, scripts, or archives.
- Never automatically open suspicious URLs on the user's machine.
- Use controlled or synthetic emails during development and demonstrations.
- Treat external threat intelligence and AI as optional; failures must not break local analysis.
- Keep evidence and score contributors visible and reproducible.
- Do not claim exact attacker identity, exact physical location, or perfect detection.
- Redact sensitive data from logs and do not send email content to third parties without authorization.
- Keep the MVP small and reliable; do not add custom LLM training, autonomous agents, multi-agent orchestration, microservices, Redis, Kafka, Kubernetes, or unnecessary cloud infrastructure.

## Planning Documents

- [docs/BLUEPRINT.md](docs/BLUEPRINT.md) - authoritative product blueprint
- [docs/API.md](docs/API.md) - API contract and lifecycle
- [docs/DATABASE.md](docs/DATABASE.md) - entities and persistence model
- [docs/THREAT_RULES.md](docs/THREAT_RULES.md) - deterministic checks and scoring
- [docs/DEMO.md](docs/DEMO.md) - five-minute offline-capable demonstration
- [sample_data/README.md](sample_data/README.md) - safe fixture plan

This repository is currently at the planning and architecture foundation stage. Application implementation should follow the phased task plan and preserve the blueprint's constraints.

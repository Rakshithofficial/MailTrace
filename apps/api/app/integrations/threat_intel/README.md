# Optional Threat Intelligence Adapters

The adapters perform read-only lookups of normalized indicators. They never submit email bodies, attachments, or files.

## Providers

- `LocalProvider`: always available offline; uses an injected fixture map and returns `unknown` for an unlisted indicator.
- `VirusTotalProvider`: optional read-only lookup for IP, domain, URL, and hash indicators.
- `UrlscanProvider`: optional read-only URL search.
- `NoOpProvider`: explicit unavailable fallback when no provider is configured.

## Environment Variables

- `VIRUSTOTAL_API_KEY`
- `URLSCAN_API_KEY`

Keys are read at runtime and are never included in normalized results. Missing keys return `status: unavailable`.

## Failure Behavior

Timeouts, rate limits, invalid responses, non-success HTTP responses, and network failures become provider results with `status: unavailable`. `ThreatIntelService` continues with all remaining providers and returns local results. Third-party results are enrichment records only; they do not become local findings or directly change the risk score.

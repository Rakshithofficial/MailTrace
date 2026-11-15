# MailTrace Five-Minute Demonstration

## Goal

Demonstrate a complete, repeatable investigation using controlled synthetic `.eml` files. The demo must work with external threat-intelligence APIs and AI disabled; those integrations are optional enhancements.

## Preparation

- Use a seeded local database and four synthetic emails from `sample_data/`.
- Keep the application on a local network or offline.
- Precompute no hidden verdicts: the visible findings and score must be produced by the documented rules.
- Have screenshots or a recorded run available only as a backup, not as the primary demonstration.

## Run of Show

1. **0:00-0:30 - Product and safety boundary**  
   Introduce MailTrace as an email threat investigation workbench. State that it analyzes inert email data, never executes attachments, never automatically opens URLs, and does not claim exact attacker identity or location.

2. **0:30-1:10 - Intake**  
   Upload a controlled phishing `.eml`. Show case creation, parsing, sender, recipients, subject, and selected headers.

3. **1:10-2:10 - Evidence and findings**  
   Show a mismatched authentication result, look-alike domain, suspicious URL, urgency language, and attachment metadata. Open a finding to show the exact evidence and rule ID.

4. **2:10-2:45 - Explainable risk**  
   Show the 0-100 score, severity, and contributor list. Explain that the score is deterministic and traceable to evidence.

5. **2:45-3:35 - Relationship intelligence**  
   Load a second synthetic campaign email. Show the shared normalized domain or attachment hash and the possible-campaign relationship with confidence wording.

6. **3:35-4:20 - Infrastructure and optional services**  
   Show approximate source/infrastructure context and the provider status. Disable the external provider to demonstrate that local findings and the investigation still work.

7. **4:20-5:00 - Explanation, response, and report**  
   Show the existing-model explanation if available, then disable it or use the fallback template. Display recommendations such as quarantine, block the indicator, search related mail, review affected users, preserve evidence, and export the report.

## Success Criteria

The audience sees one case from intake to report, at least three evidence-backed findings, a transparent score, two related synthetic emails, and successful fallback behavior. No live malicious infrastructure, real credentials, real victim data, or uncontrolled URLs are used.

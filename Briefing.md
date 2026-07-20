Build an API-first MVP for the “MAMI Compliance Checker” for TNO CoE-DSC.

CONTEXT
MAMI (Minimal Agreements for Maximal Interoperability) is a 4×3 framework: categories (Scheme mgmt, Participants mgmt, Data mgmt, Services mgmt) × dimensions (Human readable/actionable, Machine readable/actionable, Trust Anchors). MAMI includes high-level recs H-HRA-0, H-MRA-0, H-TA-0 and specific recs with codes:
S-HRA/MRA/TA-1.1/1.2/1.3
PP-HRA/MRA/TA-2.1/2.2
D-HRA/MRA/TA-3.1/3.2
SER-HRA/MRA/TA-4.1/4.2
We need a user-friendly tool that allows Data Sharing Initiative (DSI) Leaders to fill in a survey and see how their initiative scores against the MAMI Framework. We need a modular setup, so that MAMI, the Questionaire, the Logics to calculate scoring and the Presentation for DSI Leaders and Presentation for Admin (as dashboard and in a later phase a downloadable PDF report) can be expanded in a later phase.

The questionnaire and scoring must be config-driven and map answers to these codes. Use MUST/SHOULD/COULD/WON’T logic (MoSCoW). MUST findings default to CRITICAL unless overridden in config.

GOAL
Iteration 1 MVP:
- Users create accounts, register their data sharing initiative, fill in the MAMI questionnaire, update answers anytime and afterwards be able to re-generate their report.
- When ready, (re-)generate a compliance report with CRITICAL/NON_CRITICAL recommendations and evidence.
- Some checks must visit user-provided URLs (with explicit consent) and optionally run an LLM-based page analysis for evidence AND/OR use some form of Business Rules (engine) to check and cross-check answers and given evidence (in the form of URLs to online artefacts)
- Admin/Owner can log in to manage users and view the full dataset + dashboards.

REQUIREMENTS
1) API-first backend (REST + OpenAPI). Front-end is handled by another team; ensure any modern FE can integrate.
2) RBAC roles USER and ADMIN.
3) Config-driven questionnaire + versioning:
   - questions map to MAMI code, category, dimension, moscow level, scoring rules.
   - support NOT_APPLICABLE and “comply or explain”.
   - for this, utilize both a questionnaire builder and a business rule engine with WYSIWYG editor
4) Database persistence. Provide migrations/seed.
5) URL check subsystem:
   - consent required per URL; rate-limited; store snapshots (hash+timestamp).
   - implement at least: http status + keyword presence + optional LLM summarization/classification.
6) Report generator:
   - HTML in-app view + PDF export.
   - include executive summary, matrix overview, per-code findings with rationale, evidence and next steps.
7) Admin endpoints:
   - list initiatives, list users, soft delete, analytics aggregations and heatmap.
8) Reporting / Dashboarding
   - Utilize an open source, fit-for-purpose, dashboarding repository for both user- and admin reports.
9) Deployable via webinterfaces as part of a broader website (https://www.coe-dsc.nl)
10) Utilize the existing color scheme of aforementioned website.

DELIVERABLES
- Full code to deploy on web.
- README with run instructions.
- Sensible defaults and modular architecture to extend later (protocol plotting, sector variants).

DESIGN GUIDANCE
- Keep it implementable within 5 days; avoid overengineering.
- Emphasize extensibility: rules/config changes should not require code changes.
- Include audit logging for URL checks and report generation.
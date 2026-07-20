# Feature Research

**Domain:** Compliance Assessment / Survey-Based Compliance Checker (MAMI 4x3 Framework Tool)
**Researched:** 2026-02-14
**Confidence:** MEDIUM — table stakes derived from multiple WebSearch sources cross-checked against GRC tool reviews; MAMI-specific features derived from Briefing.md (project source of truth)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| User account registration + login | Users need to own their data and return to in-progress work | LOW | RBAC with USER and ADMIN roles; JWT or session-based auth |
| Initiative registration | Users represent a specific DSI; needs a named, persistent entity | LOW | One user can have one initiative in MVP; multi-initiative is v2 |
| Multi-step questionnaire with save/resume | Surveys are long; users cannot complete in a single session | MEDIUM | Auto-save on answer change; track completion percentage |
| Answer persistence across sessions | Users must be able to return to previous answers | LOW | Answers tied to initiative entity; not ephemeral |
| Questionnaire version awareness | Framework and questions change; users must know which version they answered | MEDIUM | Version stamp on submission; config-driven versioning per Briefing.md |
| MAMI framework code mapping | Each question maps to a specific MAMI code (S-HRA-1.1, etc.) | MEDIUM | Config-driven; 4 categories x 3 dimensions = 12 code groups |
| MoSCoW scoring logic | MUST/SHOULD/COULD/WON'T determines CRITICAL/NON_CRITICAL | MEDIUM | MUST findings are CRITICAL by default; config can override |
| NOT_APPLICABLE answer option | Some controls don't apply to all initiatives | LOW | Supported per Briefing.md; must not penalize score |
| Comply-or-explain option | DSI leaders can explain non-compliance rather than simply fail | MEDIUM | Free-text rationale field; shown in report findings |
| Compliance report generation | The core output of the tool; without it the survey has no value | HIGH | HTML in-app view required for MVP; PDF is standard expectation |
| Report with CRITICAL/NON_CRITICAL findings | Users need to know what requires urgent action | MEDIUM | Findings grouped by severity; each has rationale + next steps |
| Executive summary section in report | Stakeholders want a one-page overview before detail | LOW | Auto-generated from score + finding counts |
| MAMI matrix overview in report | Visual mapping of all 12 cells (4 cat x 3 dim) with status | MEDIUM | Color-coded compliance status per cell |
| Per-code findings in report | Deep-dive per MAMI recommendation code | MEDIUM | Includes answer, evidence URLs, rationale, next steps |
| Re-generate report after updating answers | Compliance status changes; report must stay current | LOW | Idempotent report generation tied to current answers |
| Admin user management | Admins must be able to list, view, and soft-delete users/initiatives | LOW | Soft delete only — no data loss |
| Admin initiative listing | Admins oversee all DSI submissions across all users | LOW | Filter, sort, search by status or user |
| Audit log for key actions | URL checks and report generation must be traceable | MEDIUM | Required explicitly in Briefing.md; timestamp + actor + action |
| OpenAPI / REST API documentation | FE is a separate team; they need a contract to integrate against | MEDIUM | OpenAPI 3.x spec; Swagger UI in dev |

### Differentiators (Competitive Advantage)

Features that set this product apart for the MAMI/TNO CoE-DSC use case. Not standard in generic GRC tools.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Config-driven questionnaire (no-code changes) | Framework can evolve without developer involvement; TNO can update MAMI mappings via config | HIGH | YAML/JSON config with question → MAMI code mapping; versioned configs |
| Visual questionnaire builder (WYSIWYG) | Empowers non-developers to modify question sets and mappings | HIGH | Admin-facing form builder; generates config; Briefing.md explicitly requires this |
| Business rules engine with visual editor | Cross-checking answers (e.g., "if Q3=No and Q5=Yes, flag inconsistency") | HIGH | Visual rule editor + underlying rules engine; Briefing.md explicitly requires this |
| URL evidence verification subsystem | Automated checking of user-provided artefact URLs (HTTP status, keyword presence) | HIGH | Requires consent per URL; rate limiting; snapshot storage (hash + timestamp) |
| LLM-based URL content analysis | AI reads the linked page and classifies whether it constitutes valid evidence | HIGH | Optional per-URL; LLM summarization/classification; adds trust to evidence chain |
| MAMI 4x3 compliance heatmap | Visual matrix showing compliance level per category/dimension cell | MEDIUM | Color gradient per cell; unique to MAMI framework structure |
| Admin analytics aggregation | Aggregate scoring patterns across all DSIs to identify systemic gaps | MEDIUM | Heatmap at population level; helps TNO CoE-DSC track ecosystem health |
| Config-controlled CRITICAL override | Framework maintainer can downgrade a MUST finding from CRITICAL via config | LOW | Important for evolving frameworks; prevents rigidity |
| Extensible framework slot (protocol variants, sector variants) | Architecture supports adding new frameworks alongside MAMI without rewriting | HIGH | Modular config per framework; future-proofs the tool per Briefing.md |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create overengineering risk or scope creep for this small-pilot, 5-day build.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time collaborative editing | Multiple stakeholders want to answer simultaneously | Adds WebSocket complexity and merge-conflict resolution; far exceeds 5-day scope | Single-user per initiative in MVP; multi-user collaboration is v2 |
| Email notifications + reminders | "Remind me to complete my questionnaire" is a natural ask | Requires email service integration, template management, unsubscribe flows; GDPR implications; not in Briefing.md | Manual workflow for pilot (<50 users); add v1.x when user base confirmed |
| SSO / OAuth2 / SAML integration | Enterprise users expect SSO; TNO may want LDAP | Auth provider integrations add significant complexity and org-specific config | Username/password with RBAC for MVP; document SSO as future extension point |
| Continuous monitoring / live compliance drift | "Know immediately when compliance changes" | Requires background job scheduling, webhook infrastructure, real-time polling; overkill for a pilot with <50 users | Report regeneration on demand (user-initiated) covers the need |
| Multi-framework simultaneous assessment | Map one questionnaire to MAMI + ISO 27001 + GDPR at once | Cross-framework mapping requires a shared control library and conflation logic; diverges from MAMI-specific mission | Extensible slot architecture (DIFFERENTIATOR) lets frameworks be added sequentially, not simultaneously |
| Public initiative comparison / benchmarking | "Show how my initiative compares to others" | Requires anonymization logic, consent flows, aggregate privacy review; adds compliance-of-the-tool risk | Admin aggregate heatmap (DIFFERENTIATOR) gives TNO the population view without exposing individual data |
| Native mobile app | Some users prefer mobile | Doubles front-end scope; API-first backend already enables mobile; this tool is primarily a desktop workflow | API-first backend enables any FE including mobile; not an MVP concern |
| Granular audit trail UI | Full change-history browser per answer field | Builds into a version-control system; significant complexity for minimal pilot value | Server-side audit log (TABLE STAKES) covers legal/traceability need; no UI browser in MVP |

---

## Feature Dependencies

```
[User Account]
    └──requires──> [Initiative Registration]
                       └──requires──> [Questionnaire (answer session)]
                                          └──requires──> [MAMI Code Mapping Config]
                                          └──requires──> [MoSCoW Scoring Logic]
                                          └──optional──> [URL Evidence Subsystem]
                                          └──optional──> [Business Rules Engine]
                                                ├──requires──> [Visual Rule Editor]
                                          └──feeds──> [Report Generator]
                                                          ├──requires──> [Executive Summary logic]
                                                          ├──requires──> [Matrix Overview (4x3)]
                                                          └──requires──> [Per-code Findings]

[Admin Account]
    └──requires──> [RBAC]
    └──feeds──> [User Management]
    └──feeds──> [Initiative Listing]
    └──feeds──> [Analytics Aggregation / Heatmap]

[Config-Driven Questionnaire]
    └──enhances──> [Visual Questionnaire Builder]
    └──requires──> [Questionnaire Versioning]

[URL Evidence Subsystem]
    └──requires──> [Consent mechanism]
    └──requires──> [Audit Log]
    └──enhances──> [LLM-based URL Analysis]

[Business Rules Engine]
    └──enhances──> [CRITICAL override per-config]
    └──requires──> [Questionnaire answer session] (needs answers to evaluate rules)

[Report Generator]
    └──enhances──> [PDF Export]
    └──enhances──> [MAMI heatmap visual]
    └──requires──> [Scoring Engine output]
```

### Dependency Notes

- **Questionnaire requires MAMI Code Mapping Config:** No answers can be stored or scored without the config that defines what each question maps to. Config must be built before any UX.
- **Report Generator requires Scoring Engine:** You cannot generate CRITICAL/NON_CRITICAL findings without first computing MoSCoW-based scores. Scoring is a backend concern, not a report concern.
- **URL Evidence Subsystem requires Consent Mechanism:** This is a hard legal dependency. URL checking without explicit per-URL consent is not acceptable for a TNO tool. Build consent before URL fetching.
- **Business Rules Engine requires Questionnaire Answers:** Rules fire against submitted answers; the engine cannot operate before the answer model exists. Implement after answer persistence is stable.
- **Visual Questionnaire Builder enhances Config-Driven Questionnaire:** The builder is a UX layer on top of the config format. The config schema must be finalized before the builder can be built.
- **Admin Heatmap requires Multiple Initiatives:** The aggregate heatmap has no meaningful data until several DSIs have submitted. Build the heatmap view early but it matures with data.
- **PDF Export depends on Report Generator:** PDF is a rendering format, not a logic feature. It can be bolted on after HTML report is working.

---

## MVP Definition

### Launch With (v1)

Minimum viable product to validate the concept with TNO CoE-DSC pilot (<50 users).

- [ ] User registration + login (USER / ADMIN roles) — needed to own and persist data
- [ ] Initiative registration — the entity that owns all questionnaire answers and reports
- [ ] Config-driven MAMI questionnaire (current version) with save/resume — the core data-collection workflow
- [ ] MoSCoW scoring engine (MUST→CRITICAL, overrideable in config) — the compliance logic
- [ ] NOT_APPLICABLE + comply-or-explain answer types — required by MAMI assessment methodology
- [ ] HTML compliance report (executive summary + matrix overview + per-code findings) — the core output that justifies the tool
- [ ] CRITICAL/NON_CRITICAL finding classification in report — the differentiating output over a generic survey
- [ ] Report re-generation on demand — keeps report in sync with answer updates
- [ ] URL evidence subsystem (HTTP check + keyword presence + consent + snapshot storage) — explicit requirement in Briefing.md
- [ ] Audit log for URL checks and report generation — explicit requirement in Briefing.md
- [ ] Admin: user list, initiative list, soft delete — minimum admin function
- [ ] REST API + OpenAPI spec — FE team dependency; blocks parallel FE development
- [ ] DB migrations + seed with current MAMI config — required for deployment

### Add After Validation (v1.x)

Features to add once core pilot is running and user feedback has been collected.

- [ ] PDF export of compliance report — add once HTML report is validated; trigger: users ask for shareable format
- [ ] LLM-based URL content analysis — add once URL subsystem is stable; trigger: evidence quality complaints
- [ ] Business rules engine + visual editor — add when cross-checking requirements are documented by TNO; trigger: false positives from simple scoring
- [ ] Visual questionnaire builder — add when TNO needs to update the MAMI question set themselves; trigger: first framework update request
- [ ] Admin analytics aggregation heatmap — add once 5+ initiatives are submitted; trigger: TNO wants ecosystem insights
- [ ] Email notifications — add if users miss deadlines during pilot; trigger: confirmed operational need

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] Multi-initiative per user — defer; single DSI per user is sufficient for pilot
- [ ] SSO / SAML / OAuth2 — defer; small pilot doesn't require enterprise auth
- [ ] Multi-framework simultaneous mapping — defer; architecture should support it but don't build in MVP
- [ ] Public benchmarking / anonymized aggregate comparison — defer; privacy implications need stakeholder sign-off
- [ ] Continuous monitoring / drift detection — defer; on-demand re-generation is sufficient for pilot cadence

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| User auth + RBAC | HIGH | LOW | P1 |
| Initiative registration | HIGH | LOW | P1 |
| Config-driven MAMI questionnaire | HIGH | MEDIUM | P1 |
| MoSCoW scoring engine | HIGH | MEDIUM | P1 |
| HTML compliance report | HIGH | HIGH | P1 |
| REST API + OpenAPI spec | HIGH | MEDIUM | P1 |
| DB migrations + seed | HIGH | LOW | P1 |
| CRITICAL/NON_CRITICAL classification | HIGH | LOW | P1 |
| NOT_APPLICABLE + comply-or-explain | MEDIUM | LOW | P1 |
| URL evidence subsystem (HTTP check + consent) | MEDIUM | HIGH | P1 |
| Audit log | MEDIUM | LOW | P1 |
| Admin user/initiative management | MEDIUM | LOW | P1 |
| Report re-generation | HIGH | LOW | P1 |
| PDF export | MEDIUM | MEDIUM | P2 |
| LLM-based URL analysis | MEDIUM | HIGH | P2 |
| Business rules engine | MEDIUM | HIGH | P2 |
| Visual rule editor | LOW | HIGH | P2 |
| Visual questionnaire builder | LOW | HIGH | P2 |
| Admin analytics heatmap | MEDIUM | MEDIUM | P2 |
| Multi-initiative per user | LOW | LOW | P3 |
| SSO / OAuth2 | LOW | HIGH | P3 |
| Multi-framework simultaneous | LOW | HIGH | P3 |
| Email notifications | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

Most direct comparators are generic GRC tools (Vanta, Drata, Secureframe, Sprinto). None are MAMI-specific. Key differentiations:

| Feature | Vanta/Drata/Secureframe (Generic GRC) | MAMI Compliance Checker | Notes |
|---------|---------------------------------------|------------------------|-------|
| Framework mapping | SOC2, ISO27001, GDPR (generic) | MAMI 4x3 (bespoke TNO framework) | No competitor covers MAMI |
| Questionnaire format | Control-to-evidence mapping | Question-to-MAMI-code mapping with MoSCoW scoring | More structured scoring methodology |
| Evidence collection | Automated integrations (GitHub, AWS, etc.) | URL-based with LLM analysis | Simpler but targeted to DSI context |
| Report format | Audit-ready SOC2 reports | CRITICAL/NON_CRITICAL matrix + executive summary | Domain-specific; not generic audit report |
| Business rules | None (pass/fail based on evidence) | Cross-answer rule engine with visual editor | More nuanced than binary pass/fail |
| Admin dashboard | User org management | Ecosystem-level analytics + heatmap across DSIs | Population-level view is unique |
| Scale | Enterprise (100s-1000s users) | Pilot (<50 users) | Simplicity is appropriate |
| Config-driven framework | Vendor-controlled | Self-service YAML/JSON + visual builder | Extensibility is unique |

---

## Sources

- [Top 12 Compliance Automation Tools 2026 - Cynomi](https://cynomi.com/learn/compliance-automation-tools/) — MEDIUM confidence (WebSearch, multiple tools cross-referenced)
- [Security Compliance Questionnaires Complete Guide 2026 - Workstreet](https://www.workstreet.com/blog/security-compliance-questionnaires) — MEDIUM confidence (WebFetch confirmed)
- [Compliance Framework Mapping Tool - Risk Cognizance](https://riskcognizance.com/blog/compliance-framework-mapping-tool-definitions-and-resources) — LOW confidence (blocked on fetch, WebSearch only)
- [Compliance Monitoring Tool 2026 - Sprinto](https://sprinto.com/blog/compliance-monitoring-tool/) — MEDIUM confidence (WebSearch, multiple sources agree)
- [How to Write a Compliance Report - V-Comply](https://www.v-comply.com/blog/compliance-report-step-by-step-guide/) — MEDIUM confidence (WebSearch, consistent with other sources)
- [12 Best GRC Tools 2026 - ConductorOne](https://www.conductorone.com/guides/best-grc-solutions/) — MEDIUM confidence (WebSearch)
- [Compliance Dashboard 2025 - MetricStream](https://www.metricstream.com/learn/compliance-dashboard.html) — MEDIUM confidence (WebSearch, consistent findings)
- [MAMI Compliance Checker Briefing.md](c:/Users/djlia/Desktop/MaMi%20Checker/Briefing.md) — HIGH confidence (project source of truth)

---
*Feature research for: MAMI Compliance Checker (TNO CoE-DSC)*
*Researched: 2026-02-14*

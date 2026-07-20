# Pitfalls Research

**Domain:** Config-driven compliance assessment tool with rule engine, URL checks, and report generation
**Researched:** 2026-02-14
**Confidence:** MEDIUM — critical pitfalls verified across multiple sources; some implementation details from training knowledge cross-checked with WebSearch

---

## Critical Pitfalls

### Pitfall 1: Questionnaire Versioning Without Answer Migration Strategy

**What goes wrong:**
The questionnaire config evolves (new questions added, MAMI codes renamed, MoSCoW levels changed), but in-progress and completed initiative answers are stored against the old question IDs. When re-generating a report, the system either silently drops unanswered questions, crashes on missing keys, or produces a score that is incomparable to earlier reports.

**Why it happens:**
Teams design config-driven questionnaires treating the config as immutable. Versioning is added as an afterthought once the first real content change is requested. By then, live answer rows in the database reference question IDs that no longer exist.

**How to avoid:**
- Snapshot the full questionnaire config at the time each initiative's answers are saved. Store `questionnaire_version` on every answer-set row and on every generated report.
- Never delete or rename question IDs in the config; instead mark them `deprecated: true` so old answers remain mappable.
- On report generation, resolve the answers against the version snapshot that was active when they were submitted, not the latest config.
- Provide a migration script (not auto-run) that maps old answer-sets to a new version when an admin explicitly requests it.

**Warning signs:**
- Any question ID change in the YAML/JSON config file.
- Report generation that queries `questions` from the live config and `answers` from the DB in the same query without version join.
- No `questionnaire_version` column in the answers table schema.

**Phase to address:**
Config foundation and database design phase — before any user-facing questionnaire is built.

---

### Pitfall 2: SSRF via the URL Check Subsystem

**What goes wrong:**
The URL checker visits user-provided URLs server-side to confirm HTTP status and keyword presence. Without proper controls, an attacker submits `http://169.254.169.254/latest/meta-data/` (AWS IMDS), `http://127.0.0.1:5432/` (internal Postgres), or any private IP range. The server fetches it, leaking cloud credentials or internal service responses. The Capital One breach was triggered by exactly this pattern.

**Why it happens:**
Developers focus on the happy path (checking a public URL) and do not model the attacker-controlled input case. HTTP client libraries follow redirects by default, enabling a two-step bypass: first URL is innocuous, redirect target is internal.

**How to avoid:**
- Resolve the DNS of the submitted URL before fetching. Reject any result that resolves to RFC 1918 ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopback (`127.0.0.0/8`), link-local (`169.254.0.0/16`), or cloud metadata IPs.
- Disable automatic redirect following in the HTTP client. Validate the redirect destination through the same IP blocklist before following it.
- Allow only `http://` and `https://` protocols. Reject `file://`, `ftp://`, `gopher://` etc. at parse time.
- Enforce a hard timeout (e.g., 5 seconds) per URL check to prevent slow-loris resource exhaustion.
- Rate-limit URL check submissions per user per time window. The briefing already requires this — implement it before the endpoint is reachable.
- Run URL checks in an isolated network context (separate container/process) with no access to internal services if infrastructure permits.

**Warning signs:**
- HTTP client instantiated with `follow_redirects=True` (default in many libraries).
- No IP validation after DNS resolution.
- URL check endpoint is callable without prior consent acknowledgement in the DB.

**Phase to address:**
URL check subsystem phase — this must be the security design for that module, not a post-MVP hardening.

---

### Pitfall 3: MoSCoW Scoring Collapse — Everything Becomes CRITICAL

**What goes wrong:**
The scoring config defaults all MUST-level questions to CRITICAL. As the MAMI config is authored, content authors (often domain experts, not developers) flag most questions as MUST because they genuinely believe all requirements are mandatory. The resulting report labels 80% of findings as CRITICAL, making the tool useless — stakeholders stop reading after the first five findings.

**Why it happens:**
MoSCoW requires strict caps enforced by the system or process. Without a validation step, the natural human tendency to mark everything as must-have goes unchecked. The problem is invisible in unit tests because the scoring engine is technically correct.

**How to avoid:**
- Add a config validation rule: warn (or hard-fail in admin tooling) when more than 50% of questions in any MAMI dimension are classified as MUST.
- Add the `CRITICAL` override capability the briefing mentions — make the default `severity: CRITICAL` for MUST, but surface it explicitly in the config so authors actively decide, rather than passively accepting the default.
- Design the executive summary in the report to show a severity distribution first — if it is all red, it forces the author to recalibrate before publishing.

**Warning signs:**
- MAMI config YAML with more than half of items set to `moscow: MUST`.
- Report preview in which every finding shows `CRITICAL` severity.
- No validation pass over the config before it is loaded.

**Phase to address:**
Scoring engine and questionnaire config authoring phase.

---

### Pitfall 4: Visual Editor Becomes a Black Box — Rules Cannot Be Tested or Debugged

**What goes wrong:**
A visual rule editor (e.g., GoRules ZEN, react-querybuilder) is embedded for admins to modify scoring rules without code changes. The rules are saved as opaque JSON blobs. When a report produces an unexpected score, no one can trace which rule fired and why. The team cannot reproduce the bug without the exact input state, and debugging requires either guessing or adding ad-hoc logging.

**Why it happens:**
Visual editors make authoring easy but rarely include an execution trace UI out of the box. Teams embed the editor and the engine separately and assume the engine's debug output will be accessible. It often is not surfaced in the admin UI.

**How to avoid:**
- Choose a rule engine that natively produces a decision trace (e.g., GoRules produces a `trace` output per rule evaluation). Surface this trace in the admin panel alongside rule execution results.
- Implement a "test rule set" mode: admin uploads a sample answer payload and sees which rules fired, what their output was, and what the final score was.
- Store the rule set version alongside each generated report (analogous to questionnaire versioning above). If a report was generated with rule set v3, it must be reproducible with v3 even if v5 is now live.

**Warning signs:**
- Rule engine integration with no test mode or debug output.
- Generated reports with no `rules_version` metadata.
- Admin UI that only shows edit/save for rules, no preview or simulation.

**Phase to address:**
Rule engine integration phase — build the debug/trace UI before the first non-trivial rule is authored.

---

### Pitfall 5: Questionnaire State Not Persisted Atomically — Partial Saves Lost

**What goes wrong:**
Users fill in the long MAMI questionnaire (12+ codes across 4 categories × 3 dimensions) in a single session or return to resume. The frontend sends a bulk "save all" on submit, or relies on the browser's localStorage. A crash, browser close, or network failure mid-session loses all progress. The briefing explicitly requires users to update answers anytime — this depends entirely on reliable partial persistence.

**Why it happens:**
Teams implement the happy path (complete submission) first and treat save-and-resume as a UX nicety to add later. The database schema is designed around complete answer sets, making partial rows hard to store.

**How to avoid:**
- Design the answer storage table to accept per-question rows (not per-initiative JSON blobs). Each answer row has `initiative_id`, `question_id`, `questionnaire_version`, `value`, `updated_at`.
- Auto-save on each answer change (debounced, 1–2 seconds). Surface a "Saving..." / "Saved" indicator in the UI.
- On page load, hydrate from the database, not localStorage. localStorage is a cache only.
- Clearly distinguish `DRAFT` (in-progress, partial) from `SUBMITTED` (report-ready) initiative states in the data model.

**Warning signs:**
- Schema with a single `answers JSON` column on the initiative table.
- Save triggered only on a "Submit" button.
- Any code path that reads answers from localStorage as the authoritative source.

**Phase to address:**
Database schema and questionnaire API phase — the row-per-answer design must be established before the first save endpoint is written.

---

### Pitfall 6: "Comply or Explain" Answers Silently Break Scoring Logic

**What goes wrong:**
The briefing requires `NOT_APPLICABLE` and "comply or explain" answer types. The scoring engine is written assuming binary Yes/No answers. When a user marks a MUST question as NOT_APPLICABLE or enters a free-text explanation instead of a compliant answer, the engine either crashes (missing case), scores it as non-compliant (unfair), or scores it as compliant (wrong). None of these are correct.

**Why it happens:**
Developers implement scoring for the common case first. The "comply or explain" path is treated as an edge case and left as a TODO. By the time real users hit it, the scoring logic is deeply tangled.

**How to avoid:**
- Define the full answer type enum before writing scoring logic: `YES`, `NO`, `NOT_APPLICABLE`, `COMPLY_OR_EXPLAIN`.
- For each MoSCoW level, explicitly define what each answer type contributes to the score. This must live in the config, not in code.
  - Suggested default: `NOT_APPLICABLE` excludes the question from the denominator; `COMPLY_OR_EXPLAIN` scores as partial compliance pending admin review.
- Write scoring engine tests with all four answer types for each MoSCoW level before building the report generator.

**Warning signs:**
- Scoring function with `if answer == 'yes':` and no `else if NOT_APPLICABLE` branch.
- No enum or type definition for valid answer values in the config schema.
- Report preview that shows `undefined` or blank for comply-or-explain answers.

**Phase to address:**
Scoring engine phase — the answer type contract must be defined at the start of this phase.

---

## Technical Debt Patterns

Shortcuts that seem reasonable under 5-day timeline pressure but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Store answers as a JSON blob per initiative | Simpler initial schema | Impossible to query per question; versioning becomes a rewrite | Never — row-per-answer is not harder to implement |
| Load latest questionnaire config on report regeneration (no version snapshot) | Simpler query | Old reports produce different results when config changes | Never — breaks reproducibility guarantee |
| Skip IP validation and rely only on URL format check | Faster to ship | SSRF vulnerability; security incident risk | Never |
| Use localStorage as primary answer store | Works without backend changes | Silent data loss on browser close; not multi-device | Only as optimistic UI cache, never authoritative |
| Hard-code MoSCoW→severity mapping in scoring code | Simpler to write | Config changes require code deploy; breaks extensibility requirement | Never — config must own this mapping |
| Skip rule-set versioning on generated reports | Less complexity | Cannot reproduce old report; audit fails | MVP only if rule engine is read-only in v1 |

---

## Integration Gotchas

Common mistakes when connecting subsystems specific to this project.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| URL check HTTP client | Follow redirects automatically (`follow_redirects=True`) | Disable auto-redirect; validate each redirect destination through IP blocklist before following |
| URL check HTTP client | Skip timeout; worker hangs on slow/unresponsive URLs | Hard timeout of 5 seconds; treat timeout as a check result, not an error |
| GoRules / rule engine | Embed only the editor, not the trace output | Wire rule engine trace into admin panel response; expose via debug endpoint |
| Visual questionnaire builder | Treat builder output as display config only | Builder output IS the authoritative question config; must be versioned and immutable once used |
| Open-source dashboarding (Metabase / Grafana / Redash) | Connect directly to production DB with write permissions | Create a read-only analytics user scoped to specific views; never expose raw tables |
| PDF generation (WeasyPrint / Puppeteer) | Assume CSS renders identically to browser | Test with actual compliance report content; SVG must be converted to PNG; table widths must be percentages |

---

## Performance Traps

Patterns that work with 50 users but become visible problems if growth occurs.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| URL checks run synchronously in request lifecycle | Report generation times out; API appears hung | Queue URL checks as background jobs; return job ID immediately; poll for completion | At first slow external URL (immediately) |
| Report generated by querying all answer rows and joining rules in application code | Report generation is slow for initiatives with many answers | Pre-aggregate scoring intermediate results; cache rendered HTML until answers change | With complex rule sets (~20+ rules) |
| Admin heatmap aggregation runs a full table scan on every page load | Dashboard is slow for admin | Compute aggregations on a schedule or trigger; cache results with TTL | At ~20+ initiatives |
| Audit log written synchronously in URL check request | URL check is slow due to DB write latency | Write audit log asynchronously (fire-and-forget with retry) | At scale, but also adds latency at 50 users if DB is slow |

---

## Security Mistakes

Domain-specific security issues beyond standard web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| URL check endpoint callable before user grants explicit per-URL consent | Privacy violation; GDPR exposure for coe-dsc.nl | Store consent record per URL+initiative in DB; URL check endpoint validates consent row exists before fetching |
| Audit log rows are UPDATE-able or DELETE-able by application role | Tamper-evident guarantee broken | Insert-only audit log table; application DB user has INSERT but not UPDATE/DELETE on audit log table |
| User A can re-generate User B's report by knowing initiative UUID | Privilege escalation | All initiative endpoints validate `initiative.owner_id == authenticated_user.id`; use opaque UUIDs not sequential IDs |
| Admin dashboard exposes raw answer text without access control | Data confidentiality breach | Admin endpoints require ADMIN role check at middleware level, not just route level |
| MAMI config file served as static asset | Exposes internal scoring weights | Serve config only through authenticated admin API; never as a public static file |

---

## UX Pitfalls

Common user experience mistakes in questionnaire and compliance tools.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Single-page questionnaire with no progress indication | Users abandon mid-way; don't know how long it takes | Show progress bar (e.g., "12 of 15 sections complete"); persist per-section, not per-submit |
| Report shows only CRITICAL findings | Compliance wins are invisible; tool feels punitive | Show full matrix with compliant (green), partial, and non-compliant cells; executive summary leads with positives |
| "Comply or explain" field is a plain text box with no guidance | Users write vague explanations that fail admin review | Provide placeholder text showing what a valid explanation looks like for that specific MAMI code |
| Report regenerated without warning when questionnaire config version changes | User is confused why their score changed | Display active questionnaire version on the initiative page; warn before regenerating if version has changed since last report |
| Admin heatmap shows initiative names without anonymization option | Privacy concern in demo contexts | Offer anonymized mode that replaces names with IDs in the heatmap |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces at demo time.

- [ ] **URL check subsystem:** HTTP status returns 200 in demo — verify the IP blocklist runs for private ranges, not just format validation. Test with `http://127.0.0.1`.
- [ ] **MoSCoW scoring:** Score displays correctly for YES/NO — verify `NOT_APPLICABLE` is excluded from denominator, not counted as zero.
- [ ] **Report regeneration:** Re-generating a report works — verify it uses the questionnaire version snapshot from when answers were saved, not the latest config.
- [ ] **Questionnaire builder:** Admin can add a question in the visual editor — verify the new question is also wired to a MAMI code and MoSCoW level, not just displayed.
- [ ] **Rule engine:** Visual rules save and load — verify a sample answer payload evaluates through the rule engine and produces a trace log, not just a final score.
- [ ] **Audit log:** URL check creates an audit row — verify the log is insert-only (try UPDATE on the audit table with the app DB user; should fail).
- [ ] **RBAC:** Admin dashboard is accessible with ADMIN role — verify it is not accessible with USER role, not just visually hidden but API-blocked.
- [ ] **Comply or explain:** Free-text explanation saves — verify it is visible in the generated report alongside the relevant finding, not silently dropped.

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Questionnaire config changed without versioning; old answers orphaned | HIGH | Write a one-off migration script mapping old question IDs to new ones; requires manual review of each changed question; flag affected initiative reports as "requires re-submission" |
| SSRF exploited before IP validation was added | HIGH | Rotate all cloud credentials immediately; audit HTTP access logs for metadata endpoint access; patch and redeploy; notify security team |
| Rules version not stored; old reports not reproducible | MEDIUM | Reconstruct rules state from git history (if config is in version control); add `rules_version` column retroactively; mark existing reports as "historical — not reproducible" |
| Answers stored as JSON blob; per-question query needed | MEDIUM | Write migration to explode JSON blobs into row-per-answer table; dual-write during transition window |
| CRITICAL inflation — all findings labelled CRITICAL | LOW | Add severity cap validation to config loader; re-run scoring with corrected config; existing reports can be regenerated |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Questionnaire versioning gap | Config foundation + DB schema phase | Schema has `questionnaire_version` on answer rows; config snapshot stored at report generation time |
| SSRF in URL checker | URL check subsystem phase | Automated test: submit `http://127.0.0.1` — expect rejection; submit private IP URL — expect rejection |
| MoSCoW scoring collapse (all CRITICAL) | Scoring engine phase | Config validator rejects MAMI configs where >50% of questions are MUST |
| Visual rule editor as black box | Rule engine integration phase | Admin can run a "test" with sample payload and sees per-rule trace output |
| Partial save data loss | DB schema + questionnaire API phase | Submit 3 answers, kill session, reload — verify 3 answers persist from DB |
| Comply-or-explain breaks scoring | Scoring engine phase | Unit test: `NOT_APPLICABLE` answer on MUST question excluded from denominator |
| Audit log tamper risk | Auth + security hardening phase | App DB user cannot UPDATE or DELETE audit_log rows |
| RBAC bypass | Auth phase | API integration test: USER role receives 403 on all `/admin/*` endpoints |

---

## Sources

- OWASP SSRF Prevention Cheat Sheet — https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html (HIGH confidence, official)
- PortSwigger SSRF tutorial — https://portswigger.net/web-security/ssrf (HIGH confidence, official)
- GoRules Open-source Business Rules Engine — https://gorules.io/ (MEDIUM confidence, official product docs)
- Form.io Form Revisions documentation — https://help.form.io/userguide/forms/form-revisions (MEDIUM confidence, official)
- SurveyCTO "Updating an existing form" documentation — https://docs.surveycto.com/02-designing-forms/01-core-concepts/10.updating.html (MEDIUM confidence, official)
- Rules Engine Best Practices — https://rulesengine.dev/article/Best_Practices_for_Implementing_a_Business_Rules_Engine.html (LOW confidence, WebSearch only)
- MoSCoW pitfalls — Highberg, AltexSoft, Hypersense aggregated findings (MEDIUM confidence, multiple sources agree)
- PDF/HTML rendering pitfalls — https://pbpython.com/pdf-reports.html + Syncfusion blog (MEDIUM confidence, multiple sources agree)
- Audit trail immutability — https://whisperit.ai/blog/audit-trail-best-practices + https://www.hubifi.com/blog/immutable-audit-log-guide (MEDIUM confidence, multiple sources agree)
- Nected Rules Engine Design Patterns — https://www.nected.ai/blog/rules-engine-design-pattern (LOW confidence, WebSearch only)

---
*Pitfalls research for: MAMI Compliance Checker — Config-driven compliance assessment tool*
*Researched: 2026-02-14*

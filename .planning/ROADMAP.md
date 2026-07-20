# Roadmap: MAMI Compliance Checker

## v1.0 — Complete ✓

Full milestone archive: [`.planning/milestones/v1.0-ROADMAP.md`](.planning/milestones/v1.0-ROADMAP.md)

Delivered 11 phases (2026-02-14 → 2026-03-15): foundation, questionnaire engine, evidence, DSI/SP participant types, frontend wizard, demo readiness (admin + password reset), Figma design, design cleanup, UX improvements, polish + admin heatmap, recommendations drawer + mail PDF report.

## Next Milestone

Not yet planned. Candidates: URL crawling subsystem (EVID-02–05), audit logging (ADMN-04), PDF download button, questionnaire visual builder.

Start with `/gsd:new-milestone` when ready.

### Phase 1: Bugfix retake-questionnaire save, CSV missing follow-up selections, separate DSI/SP aggregated heatmaps

**Goal:** Fix two confirmed bugs (stale report data on retake navigation, missing followup_selections in CSV export) and split the admin heatmap into separate DSI/SP tabs.
**Requirements**: TBD
**Depends on:** Phase 0
**Plans:** 2 plans

Plans:
- [x] 01-01-PLAN.md — Fix report.tsx stale data (merge useEffects) + WizardPage.tsx save-on-unmount
- [x] 01-02-PLAN.md — Fix admin CSV followup_selections column + DSI/SP tabbed heatmap

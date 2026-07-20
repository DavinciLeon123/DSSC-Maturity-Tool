# Phase 01 — Backlog Items

## BACKLOG-01: Automated test suite for answer-save behavior

**Priority**: Medium
**Origin**: Phase 01 human verification — save-on-unmount bugs required multiple fix iterations

### Context
Phase 01 fixed two root causes for answers not persisting on retake:
1. Stale `useEffect` dependency in `report.tsx` (merged into single `[]`-dep effect)
2. `saveMutation.mutateAsync` silently dropped during React unmount (replaced with direct `saveAnswer` call via refs)

Both bugs were caught by manual testing. Automated coverage would have caught them earlier and prevents regressions.

### What to build
A test suite (Playwright E2E or Vitest + MSW) covering the following answer-save scenarios:

| Scenario | Expected outcome |
|---|---|
| Initial take — answer all topics, click Finish | All answers persisted after page refresh |
| Initial take — answer topics, navigate away via sidebar | Answers on current topic persisted |
| Retake — change main answer, click Next through all | Changed answer visible in heatmap |
| Retake — change follow-up checkboxes only, click Next | Changed selections visible in heatmap |
| Retake — change answer on any topic, navigate away (no Next) | Changed answer still persisted |
| Retake — change follow-up checkboxes, navigate away (no Next) | Changed selections still persisted |
| Retake — answer last topic, navigate away without Finish | Last topic answers persisted |
| Retake — reach last topic, click Finish | Questionnaire submitted, heatmap reflects all answers |

### Suggested approach
- **E2E (Playwright)**: Most realistic. Spin up backend + frontend, drive the browser through each scenario, assert backend DB state or heatmap display after each.
- **Unit + MSW (Vitest)**: Faster. Mock the API layer, test that `saveAnswer` is called with the correct payloads in each scenario. Verify the unmount cleanup fires.

### Files to test
- `frontend/src/components/questionnaire/WizardPage.tsx` — unmount save logic
- `frontend/src/routes/_app/report.tsx` — fresh fetch on re-navigation
- `backend/app/api/v1/questionnaire.py` — save answer endpoint

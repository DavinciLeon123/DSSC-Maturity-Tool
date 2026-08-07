# Deferred Items — Phase 16.2

Items discovered during plan execution that are out of scope for the executing plan (not caused
by that plan's own file changes) and were not fixed, per the deviation-rules scope boundary.

## D-16.2-03-01: ESLint failure in WizardPage.tsx (unrelated to this plan)

- **Found during:** 16.2-03, Task 2 verification (`npm run lint`)
- **Symptom:** `frontend/src/components/questionnaire/WizardPage.tsx:11:10 error 'WelcomeScreen' is
  defined but never used @typescript-eslint/no-unused-vars`
- **Cause:** Concurrently running sibling plan 16.2-05 (welcome screen + subsection label work) has
  `WizardPage.tsx` modified on disk (unstaged) and a new untracked `WelcomeScreen.tsx`, mid-edit at
  the time this plan ran its verification. Confirmed via `git log`/`git status` that 16.2-03 never
  touched either file.
- **Action taken:** Not fixed — out of scope for 16.2-03 (files not in this plan's `files_modified`
  list: `frontend/src/routes/_app/about.tsx`, `frontend/src/routes/_app.tsx`). Expected to resolve
  itself once 16.2-05 finishes wiring `WelcomeScreen` into `WizardPage.tsx` and commits.
- **Follow-up:** If this lint error is still present after 16.2-05 completes and commits, it needs a
  real fix in the next plan/session that touches `WizardPage.tsx`.

# Phase 4: Context and Frontend - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 4 delivers:
1. A per-category wizard questionnaire frontend that replaces RJSF with custom Yes/Not there yet/N/A components, sub-topic sub-pages, progress step pills, and back navigation.
2. DSI/SP selection at user registration (not at initiative creation), reflected as the user's type throughout the app.
3. Optional admin-provided explanatory content (text + images) attached to categories and/or topics, stored in questionnaire config files, displayed in-questionnaire only (not in reports).

**Out of scope for Phase 4:**
- 04-02 (production design team frontend) — deferred until design team delivers assets (see Deferred Ideas).
- Admin panel for managing explanatory content — handled via config files only for now.

</domain>

<decisions>
## Implementation Decisions

### Wizard Navigation Model
- **Strictly linear**: Users must complete each category before advancing to the next. Forward is blocked until current category is done. Back is always available.
- **Within each category: sub-pages per topic**: Categories have 3 topics each. Users advance through topic 1 → topic 2 → topic 3 before advancing to the next category (not all questions at once).
- **Progress indicator: Step pills** — numbered circles at top (1 → 2 → 3 → 4), active category highlighted, completed categories marked with a checkmark.
- **Back behavior**: Going back auto-saves the current topic/category answers and preserves them. No answers are lost when navigating backwards.
- **End of last category**: Returns to the dashboard. User generates the compliance report manually from the dashboard (no auto-generate or review page).

### Follow-up Question UX
- **Trigger**: Follow-up section appears when user selects YES or NOT THERE YET. Disappears (and selections are silently cleared) when user switches to NOT APPLICABLE.
- **Appearance**: Inline expand below the question card — slides down within the same question block, no navigation required.
- **Answer option style**: Horizontal button group (three styled buttons side by side: Yes / Not there yet / Not applicable), selected button highlighted.
- **Follow-up structure**: Every follow-up ALWAYS shows BOTH:
  1. Multi-select checkboxes (from the `followup.options` list in config)
  2. A free-text "Other" field
  Both are always present together whenever a follow-up appears. There is no config variation — multi-select + Other is the universal follow-up pattern.
- **Clear on answer change**: Switching from YES/NOT_THERE_YET to NOT_APPLICABLE silently clears `followup_selections` and `followup_other` (not preserved in state).

### Explanatory Context (Category/Topic Level)
- **NOT user input**: Text notes and images in this phase are admin-provided explanatory content shown TO the user to help them understand what they're being asked — not content the user creates.
- **Level**: Optional — can be attached at category level, topic level, or both.
- **Storage**: Defined in the questionnaire JSON config files alongside category/topic definitions. Lightweight and adjustable; no database or admin UI needed now.
- **Report**: Explanatory content does NOT appear in the compliance report — in-questionnaire help only.
- **Design team handoff**: Content fields are open/adjustable so that when the design team delivers, explanatory text and images can be updated without code changes.

### DSI/SP Selection
- **At registration**: The user selects DSI or SP during signup, not on a separate initiative form. This becomes their account-level type.
- **After login**: The app reflects their type — the correct questionnaire config (DSI or SP) is loaded based on this selection.
- **Initiative creation**: The participant_type on the initiative is set from the user's chosen type at registration (not re-asked during initiative creation).

### Production Frontend (04-02)
- **Skipped for Phase 4**: Design team will not deliver within the next week. 04-02 is deferred (see Deferred Ideas).
- **RJSF**: Completely replaced by the new wizard. RJSF and its dependencies are removed. (Claude's discretion — RJSF was always a placeholder.)
- **Dashboard**: Claude's discretion on whether to update dashboard layout. Likely kept as-is; focus is on the questionnaire wizard.

### Claude's Discretion
- Dashboard layout changes (if any) — keep minimal, focus on wizard.
- RJSF removal approach (clean uninstall vs. co-existence).
- Exact styling of wizard cards, topic nav arrows, and button group states within the existing coe-dsc.nl branding.
- Whether to store explanatory content as embedded JSON objects in config or as separate Markdown strings — whichever is easier to update later.

</decisions>

<specifics>
## Specific Ideas

- Progress pills at top of wizard: `① ② ③ ④` — numbered, active one highlighted in brand color, completed ones with checkmark.
- Follow-up is universal: every triggered follow-up = checkboxes + "Other" text field, always both, no exceptions.
- DSI/SP at registration is "your role" — after login the app knows you're DSI or SP and routes questionnaire accordingly.
- Explanatory content in config: lightweight JSON — `"context_text": "..."`, `"context_image": "..."` fields on category/topic objects. Null = nothing shown.

</specifics>

<deferred>
## Deferred Ideas

- **04-02: Production frontend (design team)** — Design team components and styling deferred until assets are delivered. This becomes a future phase (e.g., Phase 4.5 or Phase 5.1). When the design team delivers, the wizard built in Phase 4 should be easily re-skinnable.
- **Admin panel for managing explanatory content** — Currently config-file based. A Phase 5/6 admin panel could allow admins to edit explanatory text/images in-app without a code deploy.

</deferred>

---

*Phase: 04-context-frontend*
*Context gathered: 2026-02-19*

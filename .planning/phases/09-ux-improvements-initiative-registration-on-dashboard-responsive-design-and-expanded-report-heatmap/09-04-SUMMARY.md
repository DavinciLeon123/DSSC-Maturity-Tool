---
plan: "09-04"
phase: "09"
status: complete
completed_at: "2026-03-09"
---

# 09-04 Summary — Expanded Heatmap (Backend + Frontend)

## Result: COMPLETE

## Tasks

| # | Task | Status |
|---|------|--------|
| 1 | Backend: add _build_topic_structure() to report_generator.py | ✓ |
| 2 | Frontend: expand HeatmapMatrix to 13 rows in report.tsx | ✓ |

## Commits

- `d3a8403` feat(09-04): add _build_topic_structure to report_generator.py
- `fa9f734` feat(09-04): expand heatmap to topic-level rows in report.tsx

## What Was Built

**Backend (`report_generator.py`):** `_build_topic_structure()` reads the MAMI framework config, groups codes by category → topic, and returns a `topic_structure` dict included in `generate_report_data()` response. Shape: `{ category: [{ topic_id, topic_label, codes[] }] }`.

**Frontend (`report.tsx`):** `HeatmapMatrix` now accepts `topicStructure` prop. Renders 13 rows: 4 navy-tinted category group headers (spanning all columns, no chips) + 9 topic rows with yes/not_yet/n_a chips per dimension. Topic label is indented (2rem left padding). `TopicEntry` and `TopicStructure` TypeScript types added.

## Key Files

- `backend/app/services/report_generator.py`
- `frontend/src/routes/_app/report.tsx`

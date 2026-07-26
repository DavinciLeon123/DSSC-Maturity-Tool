import { api } from "./api";

// Thin api-wrapper convention mirrors frontend/src/lib/questionnaire.ts —
// matches the live Phase-15-02 backend contract exactly
// (backend/app/schemas/assessment.py's AssessmentSummary).

export interface DimensionScore {
  category_id: string;
  name: string;
  score: number;
}

export interface AssessmentSummary {
  id: number;
  version: number;
  submitted_at: string;
  overall_average: number;
  dimension_scores: DimensionScore[];
}

/**
 * HIST-02: owner-scoped, version-ordered list of an initiative's SUBMITTED
 * assessment versions with per-dimension scores (D-16a/D-16b data source).
 * Thin wrapper over GET /initiatives/{id}/assessments (15-02) — the server
 * re-derives ownership (404/403) before returning any data; this function
 * assumes the caller only ever requests the current user's own initiative.
 */
export async function fetchAssessmentHistory(initiativeId: number): Promise<AssessmentSummary[]> {
  const res = await api.get<AssessmentSummary[]>(`/initiatives/${initiativeId}/assessments`);
  return res.data;
}

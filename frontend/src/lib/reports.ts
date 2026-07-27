import { api } from "./api";

// ---- Phase 16 report contract (RPRT-01/02/04) ------------------------------
// Mirrors backend/app/schemas/report.py's ReportContract/PriorityListItem/
// MaturityBand exactly — field names match verbatim, no client-side
// re-derivation of maturity band color/label from a raw score anywhere
// downstream of this fetch (RESEARCH anti-pattern, RPRT-03 prohibition).

export interface MaturityBand {
  id: string;
  label: string;
  min: number;
  max: number;
  color: string;
}

export interface DimensionScore {
  category_id: string;
  name: string;
  score: number;
}

export interface PriorityListItem {
  category_id: string;
  name: string;
  score: number;
  band_id: string;
  band_label: string;
  band_color: string;
}

export interface ReportInitiative {
  name: string;
  organization: string | null;
  contact_name: string | null;
  participant_type: string | null;
}

export interface ReportContract {
  assessment_id: number;
  version: number;
  initiative: ReportInitiative;
  dimension_scores: DimensionScore[];
  priority_list: PriorityListItem[];
  radar_chart_svg: string;
  maturity_bands: MaturityBand[];
}

/**
 * D-04: fetch the shared report contract for an initiative's submitted
 * assessment — defaults to the latest submitted version, or a specific past
 * version via assessmentId. Server-side ownership/admin-bypass re-check on
 * every request (T-16-06) — the frontend link shape grants no access itself.
 */
export async function fetchReportData(
  initiativeId: number,
  assessmentId?: number,
): Promise<ReportContract> {
  const res = await api.get<ReportContract>(`/initiatives/${initiativeId}/report/data`, {
    params: assessmentId ? { assessment_id: assessmentId } : undefined,
  });
  return res.data;
}

/**
 * Trigger report generation for an initiative.
 * The POST endpoint scores all answers, renders the HTML report, stores it,
 * and returns the rendered HTML as text.
 */
export async function generateReport(initiativeId: number): Promise<string> {
  const res = await api.post(
    `/initiatives/${initiativeId}/report`,
    null,
    {
      responseType: "text",
      headers: { Accept: "text/html" },
    },
  );
  return res.data as string;
}

/**
 * Returns the URL for the GET report endpoint.
 * Note: this endpoint requires Bearer auth, so use generateReport() + blob URL
 * approach to open in a new tab (see questionnaire.tsx).
 */
export function getReportUrl(initiativeId: number): string {
  return `${api.defaults.baseURL}/initiatives/${initiativeId}/report`;
}

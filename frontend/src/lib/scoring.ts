import { api } from "./api";

export interface Finding {
  mami_code: string;
  severity: "CRITICAL" | "NON_CRITICAL" | "";
  status: "FINDING" | "COMPLIANT" | "NOT_APPLICABLE";
}

export interface ScoreResponse {
  initiative_id: number;
  total_answers: number;
  findings: Finding[];
  critical_count: number;
  non_critical_count: number;
}

export async function triggerScoring(initiativeId: number): Promise<ScoreResponse> {
  const res = await api.post<ScoreResponse>(`/initiatives/${initiativeId}/score`);
  return res.data;
}

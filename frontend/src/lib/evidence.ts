import { api } from "./api";

export interface EvidenceItem {
  id: number;
  initiative_id: number;
  question_id: string;
  mami_code: string;
  url: string;
  created_at: string;
}

export async function submitEvidence(
  initiativeId: number,
  data: { question_id: string; mami_code: string; url: string }
): Promise<EvidenceItem> {
  const res = await api.post<EvidenceItem>(
    `/initiatives/${initiativeId}/evidence`,
    data
  );
  return res.data;
}

export async function deleteEvidence(
  initiativeId: number,
  evidenceId: number
): Promise<void> {
  await api.delete(`/initiatives/${initiativeId}/evidence/${evidenceId}`);
}

export async function fetchEvidence(initiativeId: number): Promise<EvidenceItem[]> {
  const res = await api.get<EvidenceItem[]>(
    `/initiatives/${initiativeId}/evidence`
  );
  return res.data;
}

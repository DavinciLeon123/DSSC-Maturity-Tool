import { api } from "./api";

export type AnswerValue = "YES" | "NOT_THERE_YET" | "NOT_APPLICABLE";

export interface Followup {
  trigger: AnswerValue[];
  prompt: string;
  options: string[];
  allow_other: boolean;
}

export interface Question {
  id: string;
  mami_code: string;
  text: string;
  answer_type: "yes_notyet_na";
  required: boolean;
  has_evidence: boolean;
  followup?: Followup;
}

export interface Topic {
  id: string;
  label: string;
  mami_dimension: string;
  context_text?: string | null;
  context_image?: string | null;
  questions: Question[];
}

export interface Category {
  id: string;
  label: string;
  context_text?: string | null;
  context_image?: string | null;
  topics: Topic[];
}

export interface QuestionnaireConfig {
  version: string;
  participant_type: "DSI" | "SP";
  categories: Category[];
}

// Local answer state for wizard (before save)
export interface LocalAnswer {
  answer_value: AnswerValue;
  followup_selections: string[] | null;
  followup_other: string | null;
}

// API payload sent to backend on save
export interface AnswerPayload {
  question_id: string;
  mami_code: string;
  questionnaire_version: string;
  answer_value: AnswerValue;
  followup_selections?: string[] | null;
  followup_other?: string | null;
}

export interface AnswerRecord {
  id: number;
  question_id: string;
  answer_value: string;
  rationale: string | null;
  questionnaire_version: string;
  followup_selections?: string[] | null;
  followup_other?: string | null;
}

export async function fetchQuestionnaireConfig(): Promise<QuestionnaireConfig> {
  const res = await api.get<QuestionnaireConfig>("/questionnaire/config");
  return res.data;
}

export async function fetchAnswers(initiativeId: number): Promise<AnswerRecord[]> {
  const res = await api.get<AnswerRecord[]>(`/questionnaire/initiatives/${initiativeId}/answers`);
  return res.data;
}

export async function saveAnswer(
  initiativeId: number,
  question_id: string,
  payload: AnswerPayload
): Promise<AnswerRecord> {
  const res = await api.put<AnswerRecord>(
    `/questionnaire/initiatives/${initiativeId}/answers/${question_id}`,
    payload
  );
  return res.data;
}

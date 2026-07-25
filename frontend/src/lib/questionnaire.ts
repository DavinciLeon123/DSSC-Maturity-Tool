import { api } from "./api";
import { authStore } from "./auth";

// Phase-13 backend shape: question_id/category_id/score (1-5), no participant_type
// split, no mami_code/YES-NOT_THERE_YET-NOT_APPLICABLE/followup concepts.

export interface AnswerOption {
  label: string;
  score: number;
}

export interface Question {
  id: string;
  category_id: string;
  text: string;
  // Overrides config.default_options for this question only when present.
  options?: AnswerOption[];
}

export interface Category {
  id: string;
  name: string;
  questions: Question[];
}

export interface QuestionnaireConfig {
  version: string;
  default_options: AnswerOption[];
  categories: Category[];
}

// Payload sent to PUT /questionnaire/initiatives/{id}/answers/{question_id} —
// matches backend AnswerCreate exactly.
export interface AnswerCreate {
  question_id: string;
  category_id: string;
  score: number;
}

// Matches backend AnswerRead exactly.
export interface AnswerRead {
  id: number;
  assessment_id: number;
  question_id: string;
  category_id: string;
  score: number;
  answered_at: string;
  updated_at: string;
}

export async function fetchQuestionnaireConfig(): Promise<QuestionnaireConfig> {
  const res = await api.get<QuestionnaireConfig>("/questionnaire/config");
  return res.data;
}

export async function fetchAnswers(initiativeId: number): Promise<AnswerRead[]> {
  const res = await api.get<AnswerRead[]>(`/questionnaire/initiatives/${initiativeId}/answers`);
  return res.data;
}

export async function saveAnswer(
  initiativeId: number,
  questionId: string,
  payload: AnswerCreate
): Promise<AnswerRead> {
  const res = await api.put<AnswerRead>(
    `/questionnaire/initiatives/${initiativeId}/answers/${questionId}`,
    payload
  );
  return res.data;
}

/**
 * D-07/SAVE-04: best-effort forced flush of a single pending answer on
 * `beforeunload`. Deliberately uses native `fetch` with `keepalive: true`
 * rather than `navigator.sendBeacon` — sendBeacon cannot carry an
 * `Authorization` header or use PUT, both required by this endpoint
 * (RESEARCH D-07). Also deliberately bypasses the shared `api` axios
 * instance, since axios's XHR transport does not expose the `keepalive`
 * flag. Swallows all errors — the tab is closing, there is nothing left
 * to surface to the user.
 */
export function flushAnswerBeacon(
  initiativeId: number,
  questionId: string,
  categoryId: string,
  score: number
): void {
  const token = authStore.getToken();
  const baseUrl = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000/api/v1";
  fetch(`${baseUrl}/questionnaire/initiatives/${initiativeId}/answers/${questionId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ question_id: questionId, category_id: categoryId, score }),
    keepalive: true,
  }).catch(() => {
    // Nothing to surface — the tab is closing. This is a best-effort last
    // resort; the ~1.5s debounce + Next/Back flush already cover the
    // overwhelming majority of cases.
  });
}

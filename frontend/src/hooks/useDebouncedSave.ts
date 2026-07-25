import { useCallback, useRef } from "react";
import { saveAnswer } from "../lib/questionnaire";

// SAVE-02: badge state machine. "retrying" is the transient auto-retry
// sub-state (amber); "failed" is the terminal, retries-exhausted state
// (red) that blocks Next/Submit; "rate-limited" is a distinct,
// non-escalating outcome for HTTP 429 (RESEARCH Pattern 3).
export type SaveState = "idle" | "saving" | "retrying" | "saved" | "failed" | "rate-limited";

interface PendingAnswer {
  categoryId: string;
  score: number;
}

// D-05: ~1.5s debounce, splitting the 1-2s range.
const DEBOUNCE_MS = 1500;

// Pattern 3: 3 automatic attempts, capped exponential backoff, then a
// terminal state requiring the manual "Retry save" button.
const RETRY_DELAYS_MS = [1000, 2000, 4000];

function getStatusCode(err: unknown): number | undefined {
  if (typeof err === "object" && err !== null && "response" in err) {
    const response = (err as { response?: { status?: number } }).response;
    return response?.status;
  }
  return undefined;
}

/**
 * SAVE-01/SAVE-02: per-question debounced save with a retry-with-backoff
 * state machine. Each question_id gets its own debounce timer (useRef-keyed
 * map) so answering question B never cancels or resets question A's
 * pending save.
 */
export function useDebouncedSave(
  initiativeId: number,
  onStateChange: (questionId: string, state: SaveState) => void
) {
  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const pending = useRef<Record<string, PendingAnswer>>({});

  const saveWithRetry = useCallback(
    async (questionId: string, categoryId: string, score: number): Promise<void> => {
      for (let attempt = 0; attempt <= RETRY_DELAYS_MS.length; attempt++) {
        try {
          onStateChange(questionId, attempt === 0 ? "saving" : "retrying");
          await saveAnswer(initiativeId, questionId, {
            question_id: questionId,
            category_id: categoryId,
            score,
          });
          onStateChange(questionId, "saved");
          return;
        } catch (err: unknown) {
          const status = getStatusCode(err);
          if (status === 429) {
            // Non-escalating: a 429 does not consume one of the 3 auto-retry
            // attempts — retrying immediately into a rate limit only makes
            // it worse (RESEARCH Pattern 3 / Anti-Patterns).
            onStateChange(questionId, "rate-limited");
            return;
          }
          if (attempt === RETRY_DELAYS_MS.length) {
            onStateChange(questionId, "failed");
            return;
          }
          await new Promise((resolve) => setTimeout(resolve, RETRY_DELAYS_MS[attempt]));
        }
      }
    },
    [initiativeId, onStateChange]
  );

  const flush = useCallback(
    (questionId: string): Promise<void> => {
      const entry = pending.current[questionId];
      if (!entry) return Promise.resolve();
      clearTimeout(timers.current[questionId]);
      delete timers.current[questionId];
      delete pending.current[questionId];
      return saveWithRetry(questionId, entry.categoryId, entry.score);
    },
    [saveWithRetry]
  );

  const schedule = useCallback(
    (questionId: string, categoryId: string, score: number): void => {
      // Last-write-wins per question: overwriting `pending` and resetting
      // the timer means only the latest value within the debounce window
      // is ever saved.
      pending.current[questionId] = { categoryId, score };
      clearTimeout(timers.current[questionId]);
      timers.current[questionId] = setTimeout(() => {
        void flush(questionId);
      }, DEBOUNCE_MS);
    },
    [flush]
  );

  const flushAll = useCallback((): Promise<void[]> => {
    const questionIds = Object.keys(pending.current);
    return Promise.all(questionIds.map((id) => flush(id)));
  }, [flush]);

  return { schedule, flush, flushAll };
}

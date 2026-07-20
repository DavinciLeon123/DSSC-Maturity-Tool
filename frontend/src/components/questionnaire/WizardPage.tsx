import { useState, useMemo, useEffect, useRef } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { Grid } from "antd";
import type {
  QuestionnaireConfig,
  AnswerRecord,
  LocalAnswer,
  AnswerValue,
} from "../../lib/questionnaire";
import { saveAnswer } from "../../lib/questionnaire";
import { api } from "../../lib/api";
import { StepPills } from "./StepPills";
import { QuestionCard } from "./QuestionCard";
import { ContextCallout } from "./ContextCallout";

const { useBreakpoint } = Grid;

type SaveBadgeState = "idle" | "saving" | "saved" | "failed" | "rate-limited";

interface AutosaveBadgeProps {
  state: SaveBadgeState;
}

function AutosaveBadge({ state }: AutosaveBadgeProps) {
  if (state === "saving") {
    return (
      <span
        style={{
          fontSize: "0.75rem",
          color: "rgba(6,0,79,0.5)",
          fontFamily: "'Rubik', sans-serif",
        }}
      >
        Saving...
      </span>
    );
  }
  if (state === "saved") {
    return (
      <span
        style={{
          fontSize: "0.75rem",
          color: "#399e5a",
          fontWeight: 500,
          fontFamily: "'Rubik', sans-serif",
        }}
      >
        Saved ✓
      </span>
    );
  }
  if (state === "failed") {
    return (
      <span
        style={{
          fontSize: "0.75rem",
          color: "#F59E0B",
          fontWeight: 500,
          fontFamily: "'Rubik', sans-serif",
        }}
      >
        Save failed — retrying
      </span>
    );
  }
  if (state === "rate-limited") {
    return (
      <span
        style={{
          fontSize: "0.75rem",
          color: "#F59E0B",
          fontWeight: 500,
          fontFamily: "'Rubik', sans-serif",
        }}
      >
        Too many saves — slow down
      </span>
    );
  }
  return null;
}

interface Props {
  config: QuestionnaireConfig;
  initiativeId: number;
  savedAnswers: AnswerRecord[];
}

export function WizardPage({ config, initiativeId, savedAnswers }: Props) {
  const navigate = useNavigate();
  const [categoryIndex, setCategoryIndex] = useState(0);
  const [topicIndex, setTopicIndex] = useState(0);
  const [isSaving, setIsSaving] = useState(false);
  const [badgeState, setBadgeState] = useState<SaveBadgeState>("idle");
  const [submitted, setSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);

  // Mobile detection — screens.md === false means explicitly < 768px (not undefined on first render)
  const screens = useBreakpoint();
  const isMobile = screens.md === false;

  // Local answers state — initialized from savedAnswers on mount
  const [localAnswers, setLocalAnswers] = useState<Record<string, LocalAnswer>>(() => {
    const map: Record<string, LocalAnswer> = {};
    savedAnswers.forEach((a) => {
      map[a.question_id] = {
        answer_value: a.answer_value as AnswerValue,
        followup_selections: a.followup_selections ?? null,
        followup_other: a.followup_other ?? null,
      };
    });
    return map;
  });

  // Re-initialize local answers if savedAnswers prop changes (e.g. after refetch)
  useEffect(() => {
    setLocalAnswers((prev) => {
      const map: Record<string, LocalAnswer> = { ...prev };
      savedAnswers.forEach((a) => {
        // Only overwrite if not already in local state (don't clobber unsaved edits)
        if (!map[a.question_id]) {
          map[a.question_id] = {
            answer_value: a.answer_value as AnswerValue,
            followup_selections: a.followup_selections ?? null,
            followup_other: a.followup_other ?? null,
          };
        }
      });
      return map;
    });
  }, [savedAnswers]);

  const saveMutation = useMutation({
    mutationFn: async ({
      questionId,
      mamiCode,
      answer,
    }: {
      questionId: string;
      mamiCode: string;
      answer: LocalAnswer;
    }) => {
      setBadgeState("saving");
      return saveAnswer(initiativeId, questionId, {
        question_id: questionId,
        mami_code: mamiCode,
        questionnaire_version: config.version,
        answer_value: answer.answer_value,
        followup_selections: answer.followup_selections,
        followup_other: answer.followup_other,
      });
    },
    onSuccess: () => {
      setBadgeState("saved");
      // Auto-clear "Saved" back to idle after 2 seconds
      setTimeout(() => setBadgeState("idle"), 2000);
    },
    onError: (error: unknown) => {
      const status = (error as { response?: { status?: number } }).response?.status;
      if (status === 429) {
        setBadgeState("rate-limited");
        // Auto-retry resets badge to idle after 3 seconds (per CONTEXT.md locked decision)
        setTimeout(() => {
          setBadgeState("idle");
        }, 3000);
      } else {
        setBadgeState("failed");
      }
    },
  });

  const submitMutation = useMutation({
    mutationFn: () => api.post(`/initiatives/${initiativeId}/submit`),
    onSuccess: () => setSubmitted(true),
    onError: () => setSubmitError("Submission failed — please try again."),
  });

  const currentCategory = config.categories[categoryIndex];
  const currentTopic = currentCategory.topics[topicIndex];

  // Compute completed category IDs from local answers
  const completedCategoryIds = useMemo(() => {
    const completed = new Set<string>();
    config.categories.forEach((cat) => {
      const requiredIds = cat.topics
        .flatMap((t) => t.questions)
        .filter((q) => q.required)
        .map((q) => q.id);
      if (requiredIds.length > 0 && requiredIds.every((id) => localAnswers[id]?.answer_value)) {
        completed.add(cat.id);
      }
    });
    return completed;
  }, [config, localAnswers]);

  // Check if current topic has all required questions answered
  const isCurrentTopicComplete = useMemo(() => {
    const requiredIds = currentTopic.questions
      .filter((q) => q.required)
      .map((q) => q.id);
    return requiredIds.every((id) => localAnswers[id]?.answer_value);
  }, [currentTopic, localAnswers]);

  const isLastTopic = topicIndex === currentCategory.topics.length - 1;
  const isLastCategory = categoryIndex === config.categories.length - 1;
  const isFinish = isLastTopic && isLastCategory;

  // Forward blocking: disabled when current topic is incomplete or badge is saving
  const isNextDisabled = !isCurrentTopicComplete || isSaving || badgeState === "saving";
  const isBackDisabled = categoryIndex === 0 && topicIndex === 0;

  async function saveCurrentTopic() {
    const questionsToSave = currentTopic.questions.filter(
      (q) => localAnswers[q.id]?.answer_value
    );
    await Promise.all(
      questionsToSave.map((q) =>
        saveMutation.mutateAsync({
          questionId: q.id,
          mamiCode: q.mami_code,
          answer: localAnswers[q.id],
        })
      )
    );
  }

  // Track latest localAnswers and currentTopic in refs for use during unmount cleanup.
  // Cannot use saveMutation during unmount — TanStack Query tears down the observer on unmount.
  const localAnswersRef = useRef(localAnswers);
  const currentTopicRef = useRef(currentTopic);
  useEffect(() => { localAnswersRef.current = localAnswers; });
  useEffect(() => { currentTopicRef.current = currentTopic; });

  // On unmount (nav-away), fire-and-forget save of the current topic state via raw API call.
  useEffect(() => {
    return () => {
      const topic = currentTopicRef.current;
      const answers = localAnswersRef.current;
      const questionsToSave = topic.questions.filter((q) => answers[q.id]?.answer_value);
      questionsToSave.forEach((q) => {
        void saveAnswer(initiativeId, q.id, {
          question_id: q.id,
          mami_code: q.mami_code,
          questionnaire_version: config.version,
          answer_value: answers[q.id].answer_value,
          followup_selections: answers[q.id].followup_selections,
          followup_other: answers[q.id].followup_other,
        });
      });
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleNext() {
    if (isNextDisabled) return;
    window.scrollTo(0, 0);
    setIsSaving(true);
    try {
      await saveCurrentTopic();
      if (isFinish) {
        // Call submit endpoint instead of navigating directly to dashboard
        await submitMutation.mutateAsync();
        // setSubmitted(true) is handled by onSuccess — component re-renders with confirmation
      } else if (isLastTopic) {
        setCategoryIndex((c) => c + 1);
        setTopicIndex(0);
      } else {
        setTopicIndex((t) => t + 1);
      }
    } finally {
      setIsSaving(false);
    }
  }

  async function handleBack() {
    if (isBackDisabled) return;
    window.scrollTo(0, 0);
    setIsSaving(true);
    try {
      await saveCurrentTopic();
      if (topicIndex > 0) {
        setTopicIndex((t) => t - 1);
      } else if (categoryIndex > 0) {
        const prevCat = config.categories[categoryIndex - 1];
        setCategoryIndex((c) => c - 1);
        setTopicIndex(prevCat.topics.length - 1);
      }
    } finally {
      setIsSaving(false);
    }
  }

  function handleAnswerChange(questionId: string, newValue: AnswerValue) {
    // Per Pitfall 4: compute derived values directly, don't read stale state
    const prevAnswer = localAnswers[questionId];
    const followupSelections =
      newValue === "NOT_APPLICABLE" ? null : prevAnswer?.followup_selections ?? null;
    const followupOther =
      newValue === "NOT_APPLICABLE" ? null : prevAnswer?.followup_other ?? null;

    setLocalAnswers((prev) => ({
      ...prev,
      [questionId]: {
        answer_value: newValue,
        followup_selections: followupSelections,
        followup_other: followupOther,
      },
    }));
  }

  function handleFollowupSelectionsChange(questionId: string, selections: string[]) {
    setLocalAnswers((prev) => ({
      ...prev,
      [questionId]: {
        ...prev[questionId],
        followup_selections: selections.length > 0 ? selections : null,
      },
    }));
  }

  function handleFollowupOtherChange(questionId: string, text: string) {
    setLocalAnswers((prev) => ({
      ...prev,
      [questionId]: {
        ...prev[questionId],
        followup_other: text || null,
      },
    }));
  }

  async function handleGenerateHeatmap() {
    setReportLoading(true);
    setReportError(null);
    try {
      await api.post(`/initiatives/${initiativeId}/report/data`, {});
      navigate({ to: "/report" });
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } };
      setReportError(apiErr.response?.data?.detail ?? "Failed to generate heatmap. Please try again.");
    } finally {
      setReportLoading(false);
    }
  }

  if (submitted) {
    return (
      <div
        style={{
          maxWidth: "760px",
          margin: "0 auto",
          textAlign: "center",
          padding: "4rem 2rem",
        }}
      >
        <div
          style={{
            fontSize: "3rem",
            marginBottom: "1rem",
            color: "#399e5a",
          }}
        >
          &#10003;
        </div>
        <h2
          style={{
            fontSize: "1.5rem",
            fontWeight: 700,
            color: "#06004f",
            marginBottom: "1rem",
            fontFamily: "'Rubik', sans-serif",
          }}
        >
          Thanks for completing the survey.
        </h2>
        <p
          style={{
            color: "rgba(6,0,79,0.6)",
            marginBottom: "2rem",
            fontFamily: "'Rubik', sans-serif",
          }}
        >
          Thank you for completing the MAMI Questionnaire. You can now view your MAMI
          Interoperability heatmap.
        </p>
        <button
          type="button"
          onClick={handleGenerateHeatmap}
          disabled={reportLoading}
          style={{
            padding: "0.875rem 2rem",
            background: reportLoading ? "rgba(57,158,90,0.6)" : "#399e5a",
            color: "white",
            border: "none",
            borderRadius: "8px",
            fontWeight: 600,
            fontSize: "1rem",
            cursor: reportLoading ? "not-allowed" : "pointer",
            fontFamily: "'Rubik', sans-serif",
          }}
        >
          {reportLoading ? "Generating..." : "Generate heatmap"}
        </button>
        {reportError && (
          <div
            style={{
              marginTop: "1rem",
              background: "#FEE2E2",
              color: "#991B1B",
              padding: "0.75rem 1rem",
              borderRadius: "8px",
              fontSize: "0.875rem",
              fontFamily: "'Rubik', sans-serif",
            }}
          >
            {reportError}
          </div>
        )}
      </div>
    );
  }

  // Count questions across the whole questionnaire for "Question X of Y" chip
  const allQuestionsFlat = config.categories.flatMap((cat) =>
    cat.topics.flatMap((t) => t.questions)
  );
  const currentTopicQuestionsStart =
    config.categories
      .slice(0, categoryIndex)
      .flatMap((cat) => cat.topics.flatMap((t) => t.questions)).length +
    currentCategory.topics
      .slice(0, topicIndex)
      .flatMap((t) => t.questions).length;
  const currentTopicQuestionCount = currentTopic.questions.length;
  const questionFrom = currentTopicQuestionsStart + 1;
  const questionTo = currentTopicQuestionsStart + currentTopicQuestionCount;
  const totalQuestions = allQuestionsFlat.length;

  return (
    <div
      style={{
        maxWidth: isMobile ? "100%" : "1100px",
        margin: "0 auto",
        display: "flex",
        flexDirection: isMobile ? "column" : "row",
        gap: isMobile ? "1rem" : "2rem",
        alignItems: "flex-start",
        padding: isMobile ? "0 1rem" : undefined,
      }}
    >
      {/* Left panel: progress indicator — hidden on mobile */}
      {!isMobile && (
        <StepPills
          categories={config.categories}
          currentCategoryIndex={categoryIndex}
          completedCategoryIds={completedCategoryIds}
          currentTopicIndex={topicIndex}
        />
      )}

      {/* Right: question card area */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {/* Compact mobile progress indicator — shown only on mobile */}
        {isMobile && (
          <div
            style={{
              fontSize: "0.8rem",
              color: "#666",
              marginBottom: "0.5rem",
              fontFamily: "'Rubik', sans-serif",
            }}
          >
            {config.categories[categoryIndex]?.label ?? ""} · Topic {topicIndex + 1} of {currentCategory.topics.length}
          </div>
        )}

        {/* Question card */}
        <div
          style={{
            background: "white",
            borderRadius: "16px",
            padding: "2.5rem",
            boxShadow: "0 2px 16px rgba(6,0,79,0.08)",
          }}
        >
          {/* Card top row: category title (left) + question pill (center-right) + autosave badge (right) */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              marginBottom: "0.5rem",
            }}
          >
            <h3
              style={{
                fontSize: "1.25rem",
                fontWeight: 700,
                color: "#06004f",
                margin: 0,
                fontFamily: "'Rubik', sans-serif",
                flex: 1,
              }}
            >
              {currentCategory.label}
            </h3>
            {/* Question X of Y pill — top-right of card header */}
            <span
              style={{
                background: "rgba(61,82,213,0.16)",
                color: "#3d52d5",
                padding: "0.25rem 0.75rem",
                borderRadius: "100px",
                fontSize: "0.8125rem",
                fontWeight: 500,
                whiteSpace: "nowrap",
                fontFamily: "'Rubik', sans-serif",
                alignSelf: "center",
                marginLeft: "1rem",
                marginRight: "1rem",
              }}
            >
              {currentTopicQuestionCount === 1
                ? `Question ${questionFrom} of ${totalQuestions}`
                : `Questions ${questionFrom}–${questionTo} of ${totalQuestions}`}
            </span>
            {/* Autosave badge */}
            <div style={{ minHeight: "1.25rem", paddingTop: "2px" }}>
              <AutosaveBadge state={badgeState} />
            </div>
          </div>

          {/* Topic label */}
          <div
            style={{
              marginBottom: "1.5rem",
            }}
          >
            <h4
              style={{
                fontSize: "1rem",
                fontWeight: 600,
                color: "#06004f",
                margin: 0,
                fontFamily: "'Rubik', sans-serif",
              }}
            >
              {currentTopic.label}
            </h4>
          </div>

          {/* Category-level explanatory callout (if present) */}
          <ContextCallout
            contextText={currentCategory.context_text}
            contextImage={currentCategory.context_image}
          />

          {/* Topic-level explanatory callout (if present) */}
          <ContextCallout
            contextText={currentTopic.context_text}
            contextImage={currentTopic.context_image}
          />

          {/* Submit error */}
          {submitError && (
            <div
              style={{
                background: "#FEE2E2",
                color: "#991B1B",
                padding: "0.75rem 1rem",
                borderRadius: "8px",
                marginBottom: "1rem",
                fontSize: "0.875rem",
                fontFamily: "'Rubik', sans-serif",
              }}
            >
              {submitError}
            </div>
          )}

          {/* Question cards */}
          <div>
            {currentTopic.questions.map((question) => (
              <QuestionCard
                key={question.id}
                question={question}
                answer={localAnswers[question.id]}
                onAnswerChange={handleAnswerChange}
                onFollowupSelectionsChange={handleFollowupSelectionsChange}
                onFollowupOtherChange={handleFollowupOtherChange}
              />
            ))}
          </div>

          {/* Navigation buttons */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginTop: "2rem",
              paddingTop: "1.5rem",
              borderTop: "1px solid rgba(6,0,79,0.08)",
            }}
          >
            <button
              type="button"
              onClick={handleBack}
              disabled={isBackDisabled || isSaving}
              style={{
                padding: "0.75rem 1.5rem",
                border: `1px solid ${isBackDisabled || isSaving ? "rgba(6,0,79,0.2)" : "#06004f"}`,
                borderRadius: "8px",
                background: "transparent",
                color: isBackDisabled || isSaving ? "rgba(6,0,79,0.3)" : "#06004f",
                fontFamily: "'Rubik', sans-serif",
                fontWeight: 500,
                cursor: isBackDisabled || isSaving ? "not-allowed" : "pointer",
                fontSize: "1rem",
              }}
            >
              ← Previous
            </button>

            <button
              type="button"
              onClick={handleNext}
              disabled={isNextDisabled}
              style={{
                padding: "0.75rem 1.5rem",
                border: `1px solid ${isNextDisabled ? "rgba(6,0,79,0.2)" : "#06004f"}`,
                borderRadius: "8px",
                background: isNextDisabled ? "rgba(6,0,79,0.05)" : "#06004f",
                color: isNextDisabled ? "rgba(6,0,79,0.3)" : "white",
                fontFamily: "'Rubik', sans-serif",
                fontWeight: 600,
                cursor: isNextDisabled ? "not-allowed" : "pointer",
                fontSize: "1rem",
              }}
            >
              {isSaving ? "Saving..." : isFinish ? "Finish →" : "Next →"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

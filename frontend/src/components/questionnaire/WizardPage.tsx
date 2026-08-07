import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { Grid } from "antd";
import type { AnswerOption, AnswerRead, Category, QuestionnaireConfig } from "../../lib/questionnaire";
import { flushAnswerBeacon, saveLastViewedCategory } from "../../lib/questionnaire";
import { api } from "../../lib/api";
import { useDebouncedSave, type SaveState } from "../../hooks/useDebouncedSave";
import { StepPills } from "./StepPills";
import { QuestionCard } from "./QuestionCard";
import { WelcomeScreen } from "./WelcomeScreen";
import { SubsectionLabel } from "./SubsectionLabel";

interface QuestionGroupProps {
  category: Category;
  localAnswers: Record<string, number>;
  defaultOptions: AnswerOption[];
  onAnswerChange: (questionId: string, score: number) => void;
}

/**
 * Phase 16.2, SC5: groups a category's flat questions array under its named
 * subsections (config-driven, 16.2-04). Position alone determines grouping —
 * consecutive and in existing array order, no subsection_id field on
 * individual questions. Deliberately does not touch Question X of Y,
 * answeredCount, completedCategoryIds, or StepPills — those all stay keyed
 * off the flat questions array / localAnswers, unchanged.
 *
 * A genuine component (not a plain helper function) so that forwarding
 * onAnswerChange down to QuestionCard is ordinary JSX prop-passing — the
 * same idiom the previous inline `.map` already used safely. A plain
 * function taking onAnswerChange as an argument trips eslint-plugin-react-
 * hooks's "refs" rule (it can't statically prove the ref-touching closure
 * isn't invoked synchronously during render when passed through an
 * arbitrary function call rather than as a JSX prop).
 */
function QuestionGroup({ category, localAnswers, defaultOptions, onAnswerChange }: QuestionGroupProps) {
  if (!category.subsections?.length) {
    // Defensive fallback if a category is ever missing subsections.
    return (
      <>
        {category.questions.map((q) => (
          <QuestionCard
            key={q.id}
            question={q}
            defaultOptions={defaultOptions}
            value={localAnswers[q.id] ?? null}
            onAnswerChange={onAnswerChange}
          />
        ))}
      </>
    );
  }
  const nodes: React.ReactNode[] = [];
  let idx = 0;
  category.subsections.forEach((sub, subIdx) => {
    nodes.push(<SubsectionLabel key={`sub-${subIdx}`}>{sub.name}</SubsectionLabel>);
    for (let i = 0; i < sub.count; i++) {
      const q = category.questions[idx];
      nodes.push(
        <QuestionCard
          key={q.id}
          question={q}
          defaultOptions={defaultOptions}
          value={localAnswers[q.id] ?? null}
          onAnswerChange={onAnswerChange}
        />
      );
      idx++;
    }
  });
  return <>{nodes}</>;
}

const { useBreakpoint } = Grid;

/**
 * D-09/UI-SPEC: extends (does not replace) the existing badge state
 * model. "retrying" is the transient, self-healing auto-retry sub-state
 * (amber, unchanged copy); "failed" is the terminal, retries-exhausted
 * state (red) that blocks Next/Submit and surfaces a manual "Retry save"
 * button — the two are visually and semantically distinct per D-10/D-12.
 */
function AutosaveBadge({ state, onRetry }: { state: SaveState; onRetry: () => void }) {
  const base = {
    fontSize: "0.75rem",
    fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
  } as const;

  if (state === "saving") {
    return <span style={{ ...base, color: "rgba(0,142,207,0.5)" }}>Saving...</span>;
  }
  if (state === "saved") {
    return (
      <span style={{ ...base, color: "#76b82a", fontWeight: 500 }}>Saved &#10003;</span>
    );
  }
  if (state === "retrying") {
    return (
      <span style={{ ...base, color: "#F59E0B", fontWeight: 500 }}>Save failed — retrying</span>
    );
  }
  if (state === "rate-limited") {
    return (
      <span style={{ ...base, color: "#F59E0B", fontWeight: 500 }}>
        Too many saves — slow down
      </span>
    );
  }
  if (state === "failed") {
    return (
      <span style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <span style={{ ...base, color: "#991B1B", fontWeight: 500 }}>Save failed</span>
        <button
          type="button"
          onClick={onRetry}
          style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            color: "#991B1B",
            background: "transparent",
            border: "1px solid #991B1B",
            borderRadius: "0",
            padding: "0.125rem 0.5rem",
            cursor: "pointer",
            fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
          }}
        >
          Retry save
        </button>
      </span>
    );
  }
  return null;
}

interface Props {
  config: QuestionnaireConfig;
  initiativeId: number;
  savedAnswers: AnswerRead[];
  // D-08: category the user was last viewing, persisted server-side; null
  // for a first-ever visit (resume defaults to category 0 in that case).
  lastViewedCategoryId: string | null;
}

export function WizardPage({ config, initiativeId, savedAnswers, lastViewedCategoryId }: Props) {
  const navigate = useNavigate();
  const [categoryIndex, setCategoryIndex] = useState(() => {
    if (lastViewedCategoryId == null) return 0;
    const idx = config.categories.findIndex((c) => c.id === lastViewedCategoryId);
    return idx >= 0 ? idx : 0;
  });
  const [isNavigating, setIsNavigating] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  // SC3/RESEARCH Pitfall 1: a fresh draft or a fresh retake has never had a
  // last-viewed category persisted server-side, so lastViewedCategoryId ==
  // null already reliably means "nothing to resume" — show the welcome
  // screen once, before question 1. One-way: nothing below ever sets this
  // back to true.
  const [showWelcome, setShowWelcome] = useState(lastViewedCategoryId == null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);

  // Mobile detection — screens.md === false means explicitly < 768px (not undefined on first render)
  const screens = useBreakpoint();
  const isMobile = screens.md === false;

  // Local answers: question_id -> score (1-5). Initialized from savedAnswers
  // on mount; never clobbered by a later savedAnswers refetch (local edits
  // always win over a stale server snapshot).
  const [localAnswers, setLocalAnswers] = useState<Record<string, number>>(() => {
    const map: Record<string, number> = {};
    savedAnswers.forEach((a) => {
      map[a.question_id] = a.score;
    });
    return map;
  });

  // Per-question save state (SAVE-01/SAVE-02), keyed by question_id — each
  // question debounces/retries independently (useDebouncedSave), so more
  // than one can be mid-save simultaneously.
  const [saveStates, setSaveStates] = useState<Record<string, SaveState>>({});

  // D-07/SAVE-04: tracks the latest locally-entered value for any question
  // whose most recent save has not yet been confirmed successful — this is
  // exactly the set the beforeunload handler below must flush. A ref (not
  // state) since it is only ever read synchronously inside the unload
  // handler, never rendered.
  const pendingFlushRef = useRef<Record<string, { categoryId: string; score: number }>>({});

  function handleSaveStateChange(questionId: string, state: SaveState) {
    setSaveStates((prev) => ({ ...prev, [questionId]: state }));
    if (state === "saved") {
      delete pendingFlushRef.current[questionId];
      // Auto-clear "Saved" back to idle after 2s, matching the pre-rebuild
      // single-badge behavior, now per-question.
      setTimeout(() => {
        setSaveStates((prev) => (prev[questionId] === "saved" ? { ...prev, [questionId]: "idle" } : prev));
      }, 2000);
    } else if (state === "rate-limited") {
      // Rate-limited is transient and self-clears (RESEARCH Pattern 3 /
      // CONTEXT.md locked decision) — never escalates to terminal-failed.
      setTimeout(() => {
        setSaveStates((prev) =>
          prev[questionId] === "rate-limited" ? { ...prev, [questionId]: "idle" } : prev
        );
      }, 3000);
    }
  }

  const { schedule, flush, flushAll } = useDebouncedSave(initiativeId, handleSaveStateChange);

  const submitMutation = useMutation({
    mutationFn: () => api.post(`/initiatives/${initiativeId}/submit`),
    onSuccess: () => setSubmitted(true),
    onError: () => setSubmitError("Submission failed — please try again."),
  });

  const currentCategory = config.categories[categoryIndex];
  const isLastCategory = categoryIndex === config.categories.length - 1;
  const isBackDisabled = categoryIndex === 0;

  // D-02: every question on the current category page must be answered
  // before Next unlocks.
  const isCurrentPageComplete = useMemo(
    () => currentCategory.questions.every((q) => localAnswers[q.id] !== undefined),
    [currentCategory, localAnswers]
  );

  // D-10: a terminal-failed save (anywhere, not just this page — flushAll
  // on Next/Back can surface a failure for an earlier category's answer)
  // blocks Next/Submit until it is retried successfully. There is no
  // dismiss/continue-anyway path (D-11/D-12).
  const hasTerminalFailure = useMemo(
    () => Object.values(saveStates).some((s) => s === "failed"),
    [saveStates]
  );

  const isNextDisabled = !isCurrentPageComplete || hasTerminalFailure || isNavigating;

  // D-04: overall answered-count, always derived from local answer state —
  // never a hardcoded total.
  const answeredCount = Object.keys(localAnswers).length;

  // Completed-category set for StepPills — every question in a category answered.
  const completedCategoryIds = useMemo(() => {
    const completed = new Set<string>();
    config.categories.forEach((cat) => {
      if (cat.questions.length > 0 && cat.questions.every((q) => localAnswers[q.id] !== undefined)) {
        completed.add(cat.id);
      }
    });
    return completed;
  }, [config, localAnswers]);

  function handleAnswerChange(questionId: string, score: number) {
    setLocalAnswers((prev) => ({ ...prev, [questionId]: score }));
    pendingFlushRef.current[questionId] = { categoryId: currentCategory.id, score };
    // SAVE-01/D-05: schedule a ~1.5s debounced save; answering a different
    // question never cancels this one (per-question debounce timer).
    schedule(questionId, currentCategory.id, score);
  }

  function handleRetrySave(questionId: string) {
    // A "failed" state can only exist for a question whose pendingFlushRef
    // entry was set by handleAnswerChange and never cleared (clearing only
    // happens on "saved") — so this entry is always present and carries
    // the correct category_id even if the user has since navigated to a
    // different category page (D-03 back-navigation can leave a failed
    // save behind on an earlier page).
    const pending = pendingFlushRef.current[questionId];
    if (!pending) return;
    // Manual retry re-enters the schedule/flush pipeline immediately
    // (bypassing the ~1.5s debounce window) rather than reaching into
    // useDebouncedSave's internals, which this task does not modify.
    schedule(questionId, pending.categoryId, pending.score);
    void flush(questionId);
  }

  // D-07/SAVE-04/Pitfall 2/3: beforeunload cannot await an async save — it
  // must synchronously fire one small keepalive request per still-pending
  // answer (never batched into one payload). Registered once; reads
  // pendingFlushRef.current at fire time, not a stale closure.
  useEffect(() => {
    function handleBeforeUnload() {
      Object.entries(pendingFlushRef.current).forEach(([questionId, { categoryId, score }]) => {
        flushAnswerBeacon(initiativeId, questionId, categoryId, score);
      });
    }
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [initiativeId]);

  // D-08: write the currently-viewed category UNCONDITIONALLY on every
  // categoryIndex change — this does not depend on an answer being saved
  // on that page, so navigating to a category and refreshing without
  // answering still resumes there. Deliberately not gated on any answer
  // save (no piggyback, per RESEARCH Open Question 1 / plan 15-01).
  // Phase 16.2 RESEARCH Pitfall 1: MUST also be gated on showWelcome — this
  // effect fires on mount regardless of which screen is showing, and
  // without the guard a refresh while the welcome screen is up (before
  // "Begin" is clicked) would silently persist categories[0].id as
  // last-viewed, making the next mount incorrectly compute showWelcome =
  // false. The useEffect call itself must stay unconditional (Rules of
  // Hooks); only its body is gated.
  useEffect(() => {
    if (showWelcome) return;
    saveLastViewedCategory(initiativeId, config.categories[categoryIndex].id);
  }, [categoryIndex, initiativeId, config, showWelcome]);

  // A single aggregate badge for the page header — "worst" state wins so
  // the tertiary badge (UI-SPEC Visual Hierarchy) only escalates when the
  // user actually needs to notice it.
  const aggregateBadgeState: SaveState = useMemo(() => {
    const states = Object.values(saveStates);
    if (states.includes("failed")) return "failed";
    if (states.includes("retrying")) return "retrying";
    if (states.includes("rate-limited")) return "rate-limited";
    if (states.includes("saving")) return "saving";
    if (states.includes("saved")) return "saved";
    return "idle";
  }, [saveStates]);

  const failedQuestionIds = useMemo(
    () => Object.entries(saveStates).filter(([, s]) => s === "failed").map(([id]) => id),
    [saveStates]
  );

  function handleRetryAllFailed() {
    failedQuestionIds.forEach((id) => handleRetrySave(id));
  }

  async function handleNext() {
    if (isNextDisabled) return;
    window.scrollTo(0, 0);
    setIsNavigating(true);
    try {
      // D-06: flush any pending debounced saves before navigating.
      await flushAll();
      if (isLastCategory) {
        await submitMutation.mutateAsync();
      } else {
        setCategoryIndex((c) => c + 1);
      }
    } finally {
      setIsNavigating(false);
    }
  }

  async function handleBack() {
    if (isBackDisabled) return;
    window.scrollTo(0, 0);
    setIsNavigating(true);
    try {
      await flushAll();
      setCategoryIndex((c) => c - 1);
    } finally {
      setIsNavigating(false);
    }
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

  // SC3: genuine early return — renders before StepPills/the question-card
  // layout, so the welcome screen sits outside the "Question X of Y" count
  // and the StepPills sidebar for free. Nothing else in this component ever
  // sets showWelcome back to true (Previous only decrements categoryIndex),
  // so this is a one-way gate.
  if (showWelcome) {
    return (
      <div style={{ padding: isMobile ? "0 1rem" : undefined }}>
        <WelcomeScreen onBegin={() => setShowWelcome(false)} />
      </div>
    );
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
            color: "#76b82a",
          }}
        >
          &#10003;
        </div>
        <h2
          style={{
            fontSize: "1.5rem",
            fontWeight: 700,
            color: "#008ecf",
            marginBottom: "1rem",
            fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
          }}
        >
          Thanks for completing the survey.
        </h2>
        <p
          style={{
            color: "rgba(0,142,207,0.6)",
            marginBottom: "2rem",
            fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
          }}
        >
          Thank you for completing the Dataspace Maturity Assessment. You can now view your DSSC Maturity Report.
        </p>
        <button
          type="button"
          onClick={handleGenerateHeatmap}
          disabled={reportLoading}
          style={{
            padding: "0.875rem 2rem",
            background: reportLoading ? "rgba(118,184,42,0.6)" : "#76b82a",
            color: "white",
            border: "none",
            borderRadius: "0",
            fontWeight: 600,
            fontSize: "1rem",
            cursor: reportLoading ? "not-allowed" : "pointer",
            fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
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
              fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
            }}
          >
            {reportError}
          </div>
        )}
      </div>
    );
  }

  const totalQuestions = config.categories.reduce((sum, cat) => sum + cat.questions.length, 0);
  const currentCategoryQuestionsStart = config.categories
    .slice(0, categoryIndex)
    .reduce((sum, cat) => sum + cat.questions.length, 0);
  const questionFrom = currentCategoryQuestionsStart + 1;
  const questionTo = currentCategoryQuestionsStart + currentCategory.questions.length;

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
          answeredCount={answeredCount}
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
              fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
            }}
          >
            {currentCategory.name} · {answeredCount} of {totalQuestions} answered
          </div>
        )}

        {/* Question card */}
        <div
          style={{
            background: "white",
            borderRadius: "0",
            padding: "2.5rem",
            boxShadow: "0 2px 16px rgba(0,142,207,0.08)",
          }}
        >
          {/* Card top row: category title (left) + question pill (center-right) + autosave badge (right) */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              marginBottom: "1.5rem",
            }}
          >
            <h3
              style={{
                fontSize: "1.25rem",
                fontWeight: 700,
                color: "#008ecf",
                margin: 0,
                fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
                flex: 1,
              }}
            >
              {currentCategory.name}
            </h3>
            {/* Question X of Y pill — top-right of card header */}
            <span
              style={{
                background: "rgba(0,142,207,0.16)",
                color: "#008ecf",
                padding: "0.25rem 0.75rem",
                borderRadius: "100px",
                fontSize: "0.8125rem",
                fontWeight: 500,
                whiteSpace: "nowrap",
                fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
                alignSelf: "center",
                marginLeft: "1rem",
                marginRight: "1rem",
              }}
            >
              {currentCategory.questions.length === 1
                ? `Question ${questionFrom} of ${totalQuestions}`
                : `Questions ${questionFrom}–${questionTo} of ${totalQuestions}`}
            </span>
            {/* Autosave badge */}
            <div style={{ minHeight: "1.25rem", paddingTop: "2px" }}>
              <AutosaveBadge state={aggregateBadgeState} onRetry={handleRetryAllFailed} />
            </div>
          </div>

          {/* Dimension intro box (SC4): a lighter tint variant (not the
              same solid-white card as the question cards below it) so it
              reads as framing/context rather than another question card —
              renders every time the dimension page is viewed, no dismiss/
              collapse state. intro is optional on Category (16.2-04); a
              category without one simply renders nothing here. */}
          {currentCategory.intro && (
            <div
              style={{
                background: "rgba(0,142,207,0.04)",
                borderRadius: "12px",
                padding: "1.25rem 1.5rem",
                marginBottom: "1.5rem",
                color: "#3d444b",
                fontSize: "0.9375rem",
                lineHeight: 1.6,
                fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
              }}
            >
              {currentCategory.intro}
            </div>
          )}

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
                fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
              }}
            >
              {submitError}
            </div>
          )}

          {/* Question cards, grouped under subsection eyebrow labels (SC5) */}
          <div>
            <QuestionGroup
              category={currentCategory}
              localAnswers={localAnswers}
              defaultOptions={config.default_options}
              onAnswerChange={handleAnswerChange}
            />
          </div>

          {/* Terminal-failure banner (D-10/D-11/D-12): appears next to the
              blocked Next/Submit button — no dismiss/continue-anyway path. */}
          {hasTerminalFailure && (
            <div
              style={{
                background: "#FEE2E2",
                color: "#991B1B",
                padding: "0.75rem 1rem",
                borderRadius: "8px",
                marginTop: "1rem",
                fontSize: "0.875rem",
                fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
              }}
            >
              This answer didn't save. Retry before continuing.
            </div>
          )}

          {/* Navigation buttons */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginTop: "2rem",
              paddingTop: "1.5rem",
              borderTop: "1px solid rgba(0,142,207,0.08)",
            }}
          >
            <button
              type="button"
              onClick={handleBack}
              disabled={isBackDisabled || isNavigating}
              style={{
                padding: "0.75rem 1.5rem",
                border: `1px solid ${isBackDisabled || isNavigating ? "rgba(0,142,207,0.2)" : "#008ecf"}`,
                borderRadius: "0",
                background: "transparent",
                color: isBackDisabled || isNavigating ? "rgba(0,142,207,0.3)" : "#008ecf",
                fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
                fontWeight: 500,
                cursor: isBackDisabled || isNavigating ? "not-allowed" : "pointer",
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
                border: `1px solid ${isNextDisabled ? "rgba(0,142,207,0.2)" : "#008ecf"}`,
                borderRadius: "0",
                background: isNextDisabled ? "rgba(0,142,207,0.05)" : "#008ecf",
                color: isNextDisabled ? "rgba(0,142,207,0.3)" : "white",
                fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
                fontWeight: 600,
                cursor: isNextDisabled ? "not-allowed" : "pointer",
                fontSize: "1rem",
              }}
            >
              {isNavigating ? "Saving..." : isLastCategory ? "Submit assessment →" : "Next →"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

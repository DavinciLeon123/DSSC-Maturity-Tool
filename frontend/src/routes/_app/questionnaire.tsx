import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  fetchQuestionnaireConfig,
  fetchAnswers,
  fetchLastViewedCategory,
} from "../../lib/questionnaire";
import { WizardPage } from "../../components/questionnaire/WizardPage";
import { api } from "../../lib/api";

export const Route = createFileRoute("/_app/questionnaire")({
  component: QuestionnairePage,
});

function QuestionnairePage() {
  const { data: initiative, isLoading: initiativeLoading } = useQuery({
    queryKey: ["initiative"],
    queryFn: async () => {
      const res = await api.get<{ id: number; participant_type: string }>("/initiatives/me");
      return res.data;
    },
    retry: false,
  });

  const initiativeId = initiative?.id;

  const {
    data: config,
    isLoading: configLoading,
    isError: configError,
    refetch: refetchConfig,
  } = useQuery({
    queryKey: ["questionnaire-config"],
    queryFn: fetchQuestionnaireConfig,
    enabled: !!initiativeId,
  });

  const {
    data: savedAnswers = [],
    isLoading: answersLoading,
    isError: answersError,
    refetch: refetchAnswers,
  } = useQuery({
    queryKey: ["questionnaire-answers", initiativeId],
    queryFn: () => fetchAnswers(initiativeId!),
    enabled: !!initiativeId,
  });

  // D-08: the third piece of mount state — resume position — is fetched
  // alongside config/answers so the wizard never renders category 1 and
  // then jump-cuts to the user's real last-viewed category.
  const {
    data: lastViewedCategoryId = null,
    isLoading: lastViewedLoading,
    isError: lastViewedError,
    refetch: refetchLastViewed,
  } = useQuery({
    queryKey: ["questionnaire-last-viewed-category", initiativeId],
    queryFn: () => fetchLastViewedCategory(initiativeId!),
    enabled: !!initiativeId,
  });

  if (initiativeLoading || configLoading || answersLoading || lastViewedLoading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "200px",
          color: "var(--color-text-gray)",
        }}
      >
        Loading questionnaire...
      </div>
    );
  }

  if (!initiativeId) {
    return (
      <div style={{ maxWidth: "600px", margin: "2rem auto", padding: "0 1rem" }}>
        <div
          style={{
            background: "#FEF3C7",
            border: "1px solid #F59E0B",
            borderRadius: "var(--border-radius-sm)",
            padding: "1.5rem",
          }}
        >
          <p style={{ margin: 0, color: "#92400E", fontWeight: 500 }}>
            Please create your initiative first before filling in the questionnaire.
          </p>
        </div>
      </div>
    );
  }

  // Same #991B1B-on-#FEE2E2 banner + Retry convention as autosave failures
  // (UI-SPEC "Wizard initial mount / config or answers fetch" row) — no
  // separate error language invented for the mount-fetch path.
  if (configError || answersError || lastViewedError || !config) {
    return (
      <div style={{ maxWidth: "600px", margin: "2rem auto", padding: "0 1rem" }}>
        <div
          style={{
            background: "#FEE2E2",
            color: "#991B1B",
            padding: "1rem 1.5rem",
            borderRadius: "8px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "1rem",
            fontFamily: "'Rubik', sans-serif",
          }}
        >
          <span>Failed to load questionnaire. Please try again.</span>
          <button
            type="button"
            onClick={() => {
              void refetchConfig();
              void refetchAnswers();
              void refetchLastViewed();
            }}
            style={{
              padding: "0.5rem 1rem",
              border: "1px solid #991B1B",
              borderRadius: "6px",
              background: "transparent",
              color: "#991B1B",
              fontWeight: 600,
              cursor: "pointer",
              fontFamily: "'Rubik', sans-serif",
              whiteSpace: "nowrap",
            }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: "2rem 1rem" }}>
      <div style={{ maxWidth: "760px", margin: "0 auto", marginBottom: "2rem" }}>
        <h1
          style={{
            fontSize: "1.75rem",
            fontWeight: 700,
            color: "var(--color-navy)",
            margin: "0 0 0.5rem 0",
          }}
        >
          MAMI Questionnaire
        </h1>
      </div>

      <WizardPage
        config={config}
        initiativeId={initiativeId}
        savedAnswers={savedAnswers}
        lastViewedCategoryId={lastViewedCategoryId}
      />
    </div>
  );
}

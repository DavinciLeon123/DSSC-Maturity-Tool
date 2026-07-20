import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { fetchQuestionnaireConfig, fetchAnswers } from "../../lib/questionnaire";
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

  const { data: config, isLoading: configLoading } = useQuery({
    queryKey: ["questionnaire-config"],
    queryFn: fetchQuestionnaireConfig,
    enabled: !!initiativeId,
  });

  const { data: savedAnswers = [], isLoading: answersLoading } = useQuery({
    queryKey: ["questionnaire-answers", initiativeId],
    queryFn: () => fetchAnswers(initiativeId!),
    enabled: !!initiativeId,
  });

  if (initiativeLoading || configLoading || answersLoading) {
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

  if (!config) {
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
        Failed to load questionnaire configuration.
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
      />
    </div>
  );
}

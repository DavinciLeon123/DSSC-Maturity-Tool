import type { Question, LocalAnswer, AnswerValue } from "../../lib/questionnaire";
import { AnswerButtonGroup } from "./AnswerButtonGroup";
import { FollowupPanel } from "./FollowupPanel";

interface Props {
  question: Question;
  answer: LocalAnswer | undefined;
  onAnswerChange: (questionId: string, value: AnswerValue) => void;
  onFollowupSelectionsChange: (questionId: string, selections: string[]) => void;
  onFollowupOtherChange: (questionId: string, text: string) => void;
}

export function QuestionCard({
  question,
  answer,
  onAnswerChange,
  onFollowupSelectionsChange,
  onFollowupOtherChange,
}: Props) {
  const showFollowup =
    question.followup != null &&
    (answer?.answer_value === "YES" || answer?.answer_value === "NOT_THERE_YET");

  return (
    <div
      style={{
        background: "white",
        borderRadius: "var(--border-radius-sm)",
        padding: "1.5rem",
        boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
        marginBottom: "1rem",
      }}
    >
      <p
        style={{
          fontWeight: 600,
          color: "var(--color-navy)",
          marginBottom: "1rem",
          marginTop: 0,
          lineHeight: 1.5,
        }}
      >
        {question.text}
      </p>

      <AnswerButtonGroup
        value={answer?.answer_value ?? null}
        onChange={(v) => onAnswerChange(question.id, v)}
      />

      {showFollowup && question.followup && (
        <FollowupPanel
          followup={question.followup}
          selections={answer?.followup_selections ?? null}
          other={answer?.followup_other ?? null}
          onSelectionsChange={(selections) =>
            onFollowupSelectionsChange(question.id, selections)
          }
          onOtherChange={(text) => onFollowupOtherChange(question.id, text)}
        />
      )}
    </div>
  );
}

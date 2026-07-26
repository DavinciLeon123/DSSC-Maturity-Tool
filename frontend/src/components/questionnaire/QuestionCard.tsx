import type { AnswerOption, Question } from "../../lib/questionnaire";
import { AnswerButtonGroup } from "./AnswerButtonGroup";

interface Props {
  question: Question;
  // config.default_options — the RadioScale falls back to this whenever the
  // question itself has no per-question override (key_link: config is the
  // source of truth, never a hardcoded array).
  defaultOptions: AnswerOption[];
  value: number | null;
  onAnswerChange: (questionId: string, score: number) => void;
}

// A question is now just text + the radio scale — the previous followup
// and explanatory-callout branches are gone entirely (the new config schema
// has no followup/context_text/context_image fields at all).
export function QuestionCard({ question, defaultOptions, value, onAnswerChange }: Props) {
  const options = question.options ?? defaultOptions;

  return (
    <div
      style={{
        background: "white",
        borderRadius: "8px",
        padding: "1.5rem",
        boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
        marginBottom: "1rem",
      }}
    >
      <p
        style={{
          fontWeight: 400,
          fontSize: "1rem",
          lineHeight: 1.5,
          color: "#06004f",
          marginBottom: "1rem",
          marginTop: 0,
        }}
      >
        {question.text}
      </p>

      <AnswerButtonGroup
        options={options}
        value={value}
        onChange={(score) => onAnswerChange(question.id, score)}
      />
    </div>
  );
}

import type { AnswerValue } from "../../lib/questionnaire";

interface Props {
  value: AnswerValue | null;
  onChange: (v: AnswerValue) => void;
}

const ANSWER_OPTIONS: { value: AnswerValue; label: string }[] = [
  { value: "YES", label: "Yes" },
  { value: "NOT_THERE_YET", label: "Not yet, but planning to" },
  { value: "NOT_APPLICABLE", label: "Not applicable" },
];

export function AnswerButtonGroup({ value, onChange }: Props) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
      {ANSWER_OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          style={{
            padding: "1.25rem 2rem",
            border: `1px solid ${value === opt.value ? "#399e5a" : "rgba(6,0,79,0.15)"}`,
            background: value === opt.value ? "rgba(57,158,90,0.06)" : "white",
            color: "#06004f",
            borderRadius: "8px",
            fontWeight: value === opt.value ? 600 : 400,
            cursor: "pointer",
            fontSize: "1rem",
            textAlign: "left",
            fontFamily: "'Rubik', sans-serif",
            transition: "border-color 0.15s, background 0.15s",
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
          }}
        >
          {/* Selection indicator */}
          <span
            style={{
              width: "20px",
              height: "20px",
              borderRadius: "50%",
              border: `2px solid ${value === opt.value ? "#399e5a" : "rgba(6,0,79,0.25)"}`,
              background: value === opt.value ? "#399e5a" : "transparent",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            {value === opt.value && (
              <span
                style={{
                  width: "8px",
                  height: "8px",
                  borderRadius: "50%",
                  background: "white",
                  display: "block",
                }}
              />
            )}
          </span>
          {opt.label}
        </button>
      ))}
    </div>
  );
}

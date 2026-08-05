import type { AnswerOption } from "../../lib/questionnaire";

interface Props {
  options: AnswerOption[];
  value: number | null;
  onChange: (score: number) => void;
}

// QSTN-02: horizontal 5-circle radio scale, config-driven (question.options
// ?? config.default_options — never a hardcoded array). Renamed conceptually
// to "RadioScale" per UI-SPEC/RESEARCH Pattern 1; keeps the existing
// AnswerButtonGroup filename/export so QuestionCard's import stays stable.
export function AnswerButtonGroup({ options, value, onChange }: Props) {
  return (
    <div
      role="radiogroup"
      style={{
        display: "flex",
        flexDirection: "row",
        flexWrap: "wrap",
        gap: "0.5rem",
        alignItems: "flex-start",
      }}
    >
      {options.map((opt) => {
        const isSelected = value === opt.score;
        return (
          <label
            key={opt.score}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "0.5rem",
              flex: "1 1 0",
              minWidth: 0,
              fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
              cursor: "pointer",
            }}
          >
            {/* 44px hit target (WCAG 2.5.5 / theme.ts controlHeight), visible
                circle padded down to 28-32px per UI-SPEC Spacing Scale. */}
            <button
              type="button"
              role="radio"
              aria-checked={isSelected}
              onClick={() => onChange(opt.score)}
              style={{
                width: 44,
                height: 44,
                minWidth: 44,
                padding: 0,
                border: "none",
                background: "transparent",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                cursor: "pointer",
              }}
            >
              <span
                style={{
                  width: 30,
                  height: 30,
                  borderRadius: "50%",
                  border: `2px solid ${isSelected ? "#008ecf" : "rgba(0,142,207,0.25)"}`,
                  background: isSelected ? "#008ecf" : "white",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  transition: "border-color 0.15s, background 0.15s",
                }}
              >
                {isSelected && (
                  <span
                    style={{
                      width: 10,
                      height: 10,
                      borderRadius: "50%",
                      background: "white",
                      display: "block",
                    }}
                  />
                )}
              </span>
            </button>
            <span
              style={{
                fontSize: "0.8125rem",
                lineHeight: 1.4,
                textAlign: "center",
                color: "#1c2025",
                fontWeight: isSelected ? 600 : 400,
                // Wrap up to 2 lines, never ellipsis-truncate — a truncated
                // maturity-level label could hide its meaning (QSTN-02).
                overflowWrap: "break-word",
              }}
            >
              {opt.label}
            </span>
          </label>
        );
      })}
    </div>
  );
}

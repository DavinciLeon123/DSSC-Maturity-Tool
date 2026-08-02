import type { Category } from "../../lib/questionnaire";

interface Props {
  categories: Category[];
  currentCategoryIndex: number;
  completedCategoryIds: Set<string>;
  // Count of distinct answered questions across the whole questionnaire —
  // supplied by the caller (WizardPage owns answer state); the total below
  // is always derived from config, never hardcoded (D-04).
  answeredCount: number;
}

export function StepPills({
  categories,
  currentCategoryIndex,
  completedCategoryIds,
  answeredCount,
}: Props) {
  const totalQuestions = categories.reduce((sum, cat) => sum + cat.questions.length, 0);

  return (
    <div
      style={{
        width: "260px",
        flexShrink: 0,
        padding: "1.5rem",
        background: "white",
        borderRadius: "16px",
        boxShadow: "0 2px 12px rgba(0,142,207,0.06)",
        alignSelf: "flex-start",
        position: "sticky",
        top: "80px",
      }}
    >
      <p
        style={{
          fontSize: "0.875rem",
          fontWeight: 600,
          color: "#008ecf",
          marginBottom: "0.5rem",
          marginTop: 0,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          fontFamily: "'Open Sans', sans-serif",
        }}
      >
        Your progress
      </p>

      {/* D-04: overall answered-count counter, always derived from config
          (never a hardcoded 52). */}
      <p
        style={{
          fontSize: "0.8125rem",
          fontWeight: 600,
          color: "rgba(0,142,207,0.6)",
          marginBottom: "1.25rem",
          marginTop: 0,
          fontFamily: "'Open Sans', sans-serif",
        }}
      >
        {answeredCount} of {totalQuestions} answered
      </p>

      <div style={{ display: "flex", flexDirection: "column" }}>
        {categories.map((cat, i) => {
          const isActive = i === currentCategoryIndex;
          const isComplete = completedCategoryIds.has(cat.id);
          const isLast = i === categories.length - 1;

          return (
            <div key={cat.id}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                }}
              >
                {/* State circle */}
                {isComplete ? (
                  <div
                    style={{
                      width: 24,
                      height: 24,
                      borderRadius: "50%",
                      background: "#76b82a",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}
                  >
                    <span
                      style={{
                        color: "white",
                        fontSize: "14px",
                        lineHeight: 1,
                        fontWeight: 700,
                      }}
                    >
                      &#10003;
                    </span>
                  </div>
                ) : isActive ? (
                  <div
                    style={{
                      width: 24,
                      height: 24,
                      borderRadius: "50%",
                      background: "#008ecf",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}
                  >
                    <span
                      style={{
                        color: "white",
                        fontSize: "10px",
                        fontWeight: 700,
                      }}
                    >
                      {i + 1}
                    </span>
                  </div>
                ) : (
                  <div
                    style={{
                      width: 24,
                      height: 24,
                      borderRadius: "50%",
                      border: "2px solid rgba(0,142,207,0.2)",
                      background: "transparent",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}
                  >
                    <span
                      style={{
                        color: "rgba(0,142,207,0.35)",
                        fontSize: "10px",
                        fontWeight: 600,
                      }}
                    >
                      {i + 1}
                    </span>
                  </div>
                )}

                {/* Label */}
                <span
                  style={{
                    fontSize: "0.875rem",
                    fontWeight: isActive || isComplete ? 600 : 400,
                    color: isActive
                      ? "#008ecf"
                      : isComplete
                      ? "#76b82a"
                      : "rgba(0,142,207,0.45)",
                    fontFamily: "'Open Sans', sans-serif",
                    lineHeight: 1.3,
                  }}
                >
                  {cat.name}
                </span>
              </div>

              {/* Connector line between category items */}
              {!isLast && (
                <div
                  style={{
                    width: 2,
                    background: "rgba(0,142,207,0.1)",
                    minHeight: "16px",
                    margin: "3px 11px",
                  }}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

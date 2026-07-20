import type { Category } from "../../lib/questionnaire";

interface Props {
  categories: Category[];
  currentCategoryIndex: number;
  completedCategoryIds: Set<string>;
  currentTopicIndex: number;
}

export function StepPills({
  categories,
  currentCategoryIndex,
  completedCategoryIds,
  currentTopicIndex,
}: Props) {
  return (
    <div
      style={{
        width: "260px",
        flexShrink: 0,
        padding: "1.5rem",
        background: "white",
        borderRadius: "16px",
        boxShadow: "0 2px 12px rgba(6,0,79,0.06)",
        alignSelf: "flex-start",
        position: "sticky",
        top: "80px",
      }}
    >
      <p
        style={{
          fontSize: "0.875rem",
          fontWeight: 600,
          color: "#06004f",
          marginBottom: "1.25rem",
          marginTop: 0,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          fontFamily: "'Rubik', sans-serif",
        }}
      >
        Your progress
      </p>

      <div style={{ display: "flex", flexDirection: "column" }}>
        {categories.map((cat, i) => {
          const isActive = i === currentCategoryIndex;
          const isComplete = completedCategoryIds.has(cat.id);
          const isPending = !isActive && !isComplete;
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
                      background: "#399e5a",
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
                      background: "#06004f",
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
                      border: "2px solid rgba(6,0,79,0.2)",
                      background: "transparent",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}
                  >
                    <span
                      style={{
                        color: "rgba(6,0,79,0.35)",
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
                    fontWeight: isActive ? 600 : isPending ? 400 : 500,
                    color: isActive
                      ? "#06004f"
                      : isComplete
                      ? "#399e5a"
                      : "rgba(6,0,79,0.45)",
                    fontFamily: "'Rubik', sans-serif",
                    lineHeight: 1.3,
                  }}
                >
                  {cat.label}
                </span>
              </div>

              {/* Accordion: topic list for the active category */}
              {isActive && cat.topics.length > 0 && (
                <div style={{ marginLeft: "36px", marginTop: "4px" }}>
                  {cat.topics.map((topic, ti) => {
                    const isActiveTopic = ti === currentTopicIndex;
                    const isCompletedTopic = ti < currentTopicIndex;

                    return (
                      <div
                        key={topic.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "6px",
                          padding: "4px 0",
                          cursor: "default",
                        }}
                      >
                        {/* Dot indicator */}
                        {isActiveTopic ? (
                          <div
                            style={{
                              width: 6,
                              height: 6,
                              borderRadius: "50%",
                              background: "#06004f",
                              flexShrink: 0,
                            }}
                          />
                        ) : isCompletedTopic ? (
                          <div
                            style={{
                              width: 6,
                              height: 6,
                              borderRadius: "50%",
                              background: "#399e5a",
                              flexShrink: 0,
                            }}
                          />
                        ) : (
                          <div
                            style={{
                              width: 6,
                              height: 6,
                              borderRadius: "50%",
                              background: "transparent",
                              flexShrink: 0,
                            }}
                          />
                        )}

                        {/* Topic label */}
                        <span
                          style={{
                            fontSize: "0.8rem",
                            fontWeight: isActiveTopic ? 600 : 400,
                            color: isActiveTopic
                              ? "#06004f"
                              : isCompletedTopic
                              ? "#399e5a"
                              : "rgba(6,0,79,0.45)",
                            fontFamily: "'Rubik', sans-serif",
                            lineHeight: 1.3,
                          }}
                        >
                          {topic.label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Connector line between category items */}
              {!isLast && (
                <div
                  style={{
                    width: 2,
                    background: "rgba(6,0,79,0.1)",
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

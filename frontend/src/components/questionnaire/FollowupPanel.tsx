import type { Followup } from "../../lib/questionnaire";

interface Props {
  followup: Followup;
  selections: string[] | null;
  other: string | null;
  onSelectionsChange: (selections: string[]) => void;
  onOtherChange: (text: string) => void;
}

export function FollowupPanel({ followup, selections, other, onSelectionsChange, onOtherChange }: Props) {
  const currentSelections = selections ?? [];

  function handleCheckboxChange(option: string, checked: boolean) {
    if (checked) {
      onSelectionsChange([...currentSelections, option]);
    } else {
      onSelectionsChange(currentSelections.filter((s) => s !== option));
    }
  }

  return (
    <div
      style={{
        marginTop: "1rem",
        paddingTop: "1rem",
        borderTop: "1px solid #E5E7EB",
      }}
    >
      <p
        style={{
          fontSize: "0.875rem",
          fontWeight: 500,
          marginBottom: "0.75rem",
          color: "var(--color-navy)",
        }}
      >
        {followup.prompt}
      </p>

      {/* Multi-select checkboxes */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "0.5rem",
          marginBottom: "0.75rem",
        }}
      >
        {followup.options.map((opt) => (
          <label
            key={opt}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              cursor: "pointer",
            }}
          >
            <input
              type="checkbox"
              checked={currentSelections.includes(opt)}
              onChange={(e) => handleCheckboxChange(opt, e.target.checked)}
              style={{ cursor: "pointer" }}
            />
            <span style={{ fontSize: "0.875rem", color: "var(--color-navy)" }}>{opt}</span>
          </label>
        ))}
      </div>

      {/* Free-text "Other" field — always shown */}
      <input
        type="text"
        placeholder="Other (describe)..."
        value={other ?? ""}
        onChange={(e) => onOtherChange(e.target.value)}
        style={{
          width: "100%",
          padding: "0.5rem 0.75rem",
          border: "1px solid #D1D5DB",
          borderRadius: "var(--border-radius-sm)",
          fontSize: "0.875rem",
          outline: "none",
          boxSizing: "border-box",
        }}
      />
    </div>
  );
}

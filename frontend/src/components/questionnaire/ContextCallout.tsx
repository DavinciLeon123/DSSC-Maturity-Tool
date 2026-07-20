interface Props {
  contextText?: string | null;
  contextImage?: string | null;
}

export function ContextCallout({ contextText, contextImage }: Props) {
  if (!contextText && !contextImage) return null;

  return (
    <div
      style={{
        background: "#F0F4F8",
        borderLeft: "4px solid var(--color-navy)",
        padding: "1rem 1.25rem",
        borderRadius: "var(--border-radius-sm)",
        marginBottom: "1.5rem",
      }}
    >
      {contextText && (
        <p
          style={{
            margin: 0,
            fontSize: "0.9rem",
            color: "var(--color-text-gray)",
            whiteSpace: "pre-wrap",
          }}
        >
          {contextText}
        </p>
      )}
      {contextImage && (
        <img
          src={contextImage}
          alt="Context illustration"
          style={{
            maxWidth: "100%",
            marginTop: contextText ? "0.75rem" : 0,
            borderRadius: "var(--border-radius-sm)",
          }}
        />
      )}
    </div>
  );
}

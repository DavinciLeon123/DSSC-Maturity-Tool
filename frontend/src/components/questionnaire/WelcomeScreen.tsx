interface Props {
  onBegin: () => void;
}

const FONT = "'Jost', 'Helvetica Neue', Arial, sans-serif";

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h3
      style={{
        fontSize: "1rem",
        fontWeight: 700,
        color: "#008ecf",
        margin: "1.75rem 0 0.75rem",
        fontFamily: FONT,
      }}
    >
      {children}
    </h3>
  );
}

function Paragraph({ children }: { children: React.ReactNode }) {
  return (
    <p
      style={{
        fontSize: "0.9375rem",
        lineHeight: 1.6,
        color: "#3d444b",
        margin: "0 0 0.75rem",
        fontFamily: FONT,
      }}
    >
      {children}
    </p>
  );
}

function BulletList({ items }: { items: React.ReactNode[] }) {
  return (
    <ul
      style={{
        fontSize: "0.9375rem",
        lineHeight: 1.6,
        color: "#3d444b",
        margin: "0 0 0.75rem",
        paddingLeft: "1.25rem",
        fontFamily: FONT,
      }}
    >
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  );
}

/**
 * Phase 16.2, SC3: pre-question welcome screen rendering the full "Voorblad
 * questionnaire" copy verbatim from 16.2-SOURCE-CONTENT.md §4. Shown once,
 * gated by WizardPage's showWelcome state (fresh draft / fresh retake only —
 * see WizardPage.tsx's saveLastViewedCategory guard for the pitfall this
 * closes). Purely presentational: the caller owns all gating logic.
 */
export function WelcomeScreen({ onBegin }: Props) {
  return (
    <div
      style={{
        maxWidth: "760px",
        margin: "0 auto",
      }}
    >
      <div
        style={{
          background: "white",
          borderRadius: "16px",
          boxShadow: "0 2px 12px rgba(0,142,207,0.06)",
          padding: "2.5rem",
        }}
      >
        <SectionHeading>Welcome</SectionHeading>
        <Paragraph>
          Welcome to the <strong>Data Space Maturity Assessment (DSMA)</strong>. This
          self-assessment helps you evaluate the maturity of your data space initiative
          using the CEN/CLC/TS 18331:2026 Data Space Maturity Assessment standard.
        </Paragraph>

        <SectionHeading>What you will assess</SectionHeading>
        <Paragraph>
          The assessment covers six dimensions that target different aspects of maturity.
          These are:
        </Paragraph>
        <BulletList
          items={[
            "Governance",
            "Business",
            "Legal",
            "Interoperability",
            "Control over Data & Trust",
            "Value Creation.",
          ]}
        />
        <Paragraph>
          Together, these dimensions provide a comprehensive view of your data space's
          current level of maturity.
        </Paragraph>

        <SectionHeading>What you will receive</SectionHeading>
        <Paragraph>
          Upon completion you will receive a{" "}
          <strong>dashboard with the current level of maturity</strong> and the ability to
          download a separate <strong>report.</strong> This report will be used during
          value coaching by the Data Space support center.
        </Paragraph>

        <SectionHeading>Before you start</SectionHeading>
        <BulletList
          items={[
            <>
              Answer the questions based on your <strong>current state</strong> of the
              data space.
            </>,
            <>
              Select the option that best reflects what is{" "}
              <strong>implemented in practice</strong>.
            </>,
            "If multiple people are involved in your initiative, consider completing the assessment collaboratively for the most accurate result.",
          ]}
        />

        <SectionHeading>Time required</SectionHeading>
        <Paragraph>
          The assessment contains <strong>52 questions</strong> and typically takes{" "}
          <strong>15-20 minutes</strong> to complete. There are no right or wrong answers.
          The goal is to establish a realistic baseline that helps your data space
          prioritize its next steps in development and growth.
        </Paragraph>

        <div style={{ marginTop: "2rem", textAlign: "right" }}>
          <button
            type="button"
            onClick={onBegin}
            style={{
              padding: "0.875rem 2rem",
              background: "#76b82a",
              color: "white",
              border: "none",
              borderRadius: "8px",
              fontWeight: 600,
              fontSize: "1rem",
              cursor: "pointer",
              fontFamily: FONT,
            }}
          >
            Begin assessment →
          </button>
        </div>
      </div>
    </div>
  );
}

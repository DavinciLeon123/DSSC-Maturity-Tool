/**
 * Phase 16.2, SC5: small eyebrow-style sub-header placed above the first
 * question of each named subsection within a dimension page. Deliberately
 * lighter weight than the dimension's own <h3> title (WizardPage.tsx) so it
 * never visually competes with it — purely an organizational label layered
 * on top of the existing flat question loop, not a new counting unit.
 */
export function SubsectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.75rem",
        margin: "1.5rem 0 0.75rem",
      }}
    >
      <span
        style={{
          fontSize: "0.75rem",
          fontWeight: 600,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          color: "rgba(0,142,207,0.55)",
          fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
          whiteSpace: "nowrap",
        }}
      >
        {children}
      </span>
      <div style={{ flex: 1, height: "1px", background: "rgba(0,142,207,0.12)" }} />
    </div>
  );
}

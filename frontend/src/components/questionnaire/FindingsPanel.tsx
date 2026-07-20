import type { ScoreResponse } from "../../lib/scoring";

interface Props {
  score: ScoreResponse;
}

export function FindingsPanel({ score }: Props) {
  const criticalFindings = score.findings.filter((f) => f.severity === "CRITICAL");
  const nonCriticalFindings = score.findings.filter((f) => f.severity === "NON_CRITICAL");
  const isFullyCompliant = score.findings.length === 0 && score.total_answers > 0;

  return (
    <div className="findings-panel">
      <h2>Compliance Score</h2>

      <div className="findings-summary">
        <div className="findings-stat findings-stat--total">
          <span className="findings-stat__number">{score.total_answers}</span>
          <span className="findings-stat__label">Questions Answered</span>
        </div>
        <div className="findings-stat findings-stat--critical">
          <span className="findings-stat__number">{score.critical_count}</span>
          <span className="findings-stat__label">Critical Findings</span>
        </div>
        <div className="findings-stat findings-stat--non-critical">
          <span className="findings-stat__number">{score.non_critical_count}</span>
          <span className="findings-stat__label">Non-Critical Findings</span>
        </div>
      </div>

      {isFullyCompliant && (
        <div className="findings-compliant">
          All answered questions are compliant or not applicable.
        </div>
      )}

      {criticalFindings.length > 0 && (
        <section className="findings-group findings-group--critical">
          <h3>Critical Findings ({criticalFindings.length})</h3>
          <ul className="findings-list">
            {criticalFindings.map((f) => (
              <li key={f.mami_code} className="finding-item finding-item--critical">
                <span className="finding-code">{f.mami_code}</span>
                <span className="finding-severity finding-severity--critical">CRITICAL</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {nonCriticalFindings.length > 0 && (
        <section className="findings-group findings-group--non-critical">
          <h3>Non-Critical Findings ({nonCriticalFindings.length})</h3>
          <ul className="findings-list">
            {nonCriticalFindings.map((f) => (
              <li key={f.mami_code} className="finding-item finding-item--non-critical">
                <span className="finding-code">{f.mami_code}</span>
                <span className="finding-severity finding-severity--non-critical">NON-CRITICAL</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

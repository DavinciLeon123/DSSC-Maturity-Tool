import { useState } from "react";
import { submitEvidence, deleteEvidence, type EvidenceItem } from "../../lib/evidence";

interface Props {
  questionId: string;
  mamiCode: string;
  initiativeId: number;
  evidence: EvidenceItem[];
  onEvidenceChanged: () => void;
}

export function EvidenceInput({
  questionId,
  mamiCode,
  initiativeId,
  evidence,
  onEvidenceChanged,
}: Props) {
  const [url, setUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAdd() {
    if (!url.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await submitEvidence(initiativeId, {
        question_id: questionId,
        mami_code: mamiCode,
        url: url.trim(),
      });
      setUrl("");
      onEvidenceChanged();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr?.response?.data?.detail || "Failed to add evidence");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(evidenceId: number) {
    try {
      await deleteEvidence(initiativeId, evidenceId);
      onEvidenceChanged();
    } catch {
      // silent — will refresh on next query invalidation
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAdd();
    }
  }

  return (
    <div className="evidence-input">
      <label className="evidence-label">Supporting URL evidence:</label>
      {evidence.length > 0 && (
        <ul className="evidence-list">
          {evidence.map((ev) => (
            <li key={ev.id} className="evidence-item">
              <a href={ev.url} target="_blank" rel="noopener noreferrer">
                {ev.url}
              </a>
              <button
                className="btn-icon"
                onClick={() => handleDelete(ev.id)}
                title="Remove evidence URL"
                type="button"
              >
                &times;
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="evidence-form">
        <input
          type="url"
          placeholder="https://example.com/governance-doc"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={handleKeyDown}
          className="evidence-url-input"
        />
        <button
          onClick={handleAdd}
          disabled={!url.trim() || submitting}
          className="btn btn-sm"
          type="button"
        >
          {submitting ? "Adding..." : "Add URL"}
        </button>
      </div>
      {error && <p className="evidence-error">{error}</p>}
    </div>
  );
}

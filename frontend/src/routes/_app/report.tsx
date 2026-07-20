import React from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { Button, Collapse, Spin, Alert, Grid } from "antd";
import { api } from "../../lib/api";

const { useBreakpoint } = Grid;

export const Route = createFileRoute("/_app/report")({
  component: ReportPage,
});

// ---- Types ----------------------------------------------------------------

interface TopicEntry {
  topic_id: string;
  topic_label: string;
  codes: string[];
}

interface TopicStructure {
  [category: string]: TopicEntry[];
}

interface ReportInitiative {
  id: string;
  name: string;
  generated_at: string;
}

// Each cell is a map of mami_code → "yes"|"not_yet"|"n_a"|"unanswered"
type CellStatuses = Record<string, string>;

interface DimensionStatus {
  human_readable: CellStatuses;
  machine_readable: CellStatuses;
  trust_anchors: CellStatuses;
}

interface ReportMatrix {
  scheme: DimensionStatus;
  participants: DimensionStatus;
  data: DimensionStatus;
  services: DimensionStatus;
}

/** Aggregate multiple code statuses in a cell to one representative status. */
function aggregateCellStatus(cell: CellStatuses): string {
  const statuses = Object.values(cell ?? {});
  if (statuses.length === 0) return "unanswered";
  if (statuses.includes("not_yet")) return "not_yet";
  if (statuses.includes("unanswered")) return "unanswered";
  if (statuses.every((s) => s === "n_a")) return "n_a";
  if (statuses.includes("yes")) return "yes";
  return "unanswered";
}

interface ReportData {
  initiative: ReportInitiative;
  matrix: ReportMatrix;
  topic_structure: TopicStructure;
  answers: Array<{
    mami_code: string;
    answer_value: string;
    answer_label: string;
    description: string;
    evidence: string[];
  }>;
}

// ---- Status chip -----------------------------------------------------------

function StatusChip({ status }: { status: string }) {
  const cfg: Record<string, { bg: string; color: string; icon: string }> = {
    yes: { bg: "rgba(57,158,90,0.2)", color: "#399e5a", icon: "✓" },
    not_yet: { bg: "rgba(61,82,213,0.2)", color: "#3d52d5", icon: "⏳" },
    n_a: { bg: "rgba(204,204,204,0.8)", color: "#666", icon: "—" },
    unanswered: { bg: "rgba(204,204,204,0.4)", color: "#999", icon: "—" },
  };
  const c = cfg[status] ?? { bg: "rgba(204,204,204,0.4)", color: "#999", icon: "?" };
  return (
    <span
      style={{
        background: c.bg,
        color: c.color,
        borderRadius: "100px",
        padding: "6px 16px",
        fontSize: "0.85rem",
        fontFamily: "'Rubik', sans-serif",
        display: "inline-flex",
        alignItems: "center",
        gap: "6px",
        fontWeight: 500,
        whiteSpace: "nowrap",
        minWidth: "90px",
        justifyContent: "center",
      }}
    >
      <span style={{ fontSize: "1rem" }}>{c.icon}</span>
      <span>{status === "yes" ? "Yes" : status === "not_yet" ? "Not yet" : status === "n_a" ? "N/A" : status === "unanswered" ? "Unanswered" : status}</span>
    </span>
  );
}

// ---- Heatmap matrix -------------------------------------------------------

const CATEGORY_LABELS: Record<string, string> = {
  scheme: "Scheme",
  participants: "Participants",
  data: "Data",
  services: "Services",
};

const DIMENSION_LABELS = [
  { key: "human_readable" as const, label: "Human readability" },
  { key: "machine_readable" as const, label: "Machine readability" },
  { key: "trust_anchors" as const, label: "Trust anchors" },
];

const DIMENSION_LABELS_MOBILE: Record<string, string> = {
  human_readable: "HR",
  machine_readable: "MR",
  trust_anchors: "TA",
};

function HeatmapMatrix({ matrix, topicStructure, isMobile }: { matrix: ReportMatrix; topicStructure: TopicStructure; isMobile: boolean }) {
  const categories = Object.keys(CATEGORY_LABELS) as Array<keyof ReportMatrix>;
  const gridCols = isMobile ? "120px repeat(3, 1fr)" : "200px repeat(3, 1fr)";

  return (
    <div>
      {/* Header row */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: gridCols,
          background: "#06004f",
          borderRadius: "10px 10px 0 0",
          padding: "12px 16px",
          gap: "8px",
        }}
      >
        <div />
        {DIMENSION_LABELS.map((dim) => (
          <div
            key={dim.key}
            style={{
              color: "white",
              fontFamily: "'Rubik', sans-serif",
              fontWeight: 600,
              fontSize: "0.85rem",
              textAlign: "center",
            }}
          >
            {isMobile ? DIMENSION_LABELS_MOBILE[dim.key] : dim.label}
          </div>
        ))}
      </div>

      {/* Category group headers + topic rows */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: gridCols,
        }}
      >
        {categories.map((cat) => (
          <React.Fragment key={cat}>
            {/* Category group header row — no chips, navy background */}
            <div
              style={{
                gridColumn: "1 / -1",
                background: "rgba(6,0,79,0.08)",
                padding: "10px 16px",
                fontFamily: "'Rubik', sans-serif",
                fontWeight: 600,
                fontSize: "0.9rem",
                color: "#06004f",
                borderBottom: "1px solid rgba(6,0,79,0.12)",
              }}
            >
              {CATEGORY_LABELS[cat]}
            </div>

            {/* Topic rows */}
            {(topicStructure[cat] ?? []).map((topic) => (
              <React.Fragment key={topic.topic_id}>
                {/* Topic label cell */}
                <div
                  style={{
                    padding: "10px 16px 10px 2rem",
                    fontFamily: "'Rubik', sans-serif",
                    fontSize: "0.875rem",
                    color: "#333",
                    borderBottom: "1px solid #f0f0f0",
                    display: "flex",
                    alignItems: "center",
                  }}
                >
                  {topic.topic_label}
                </div>

                {/* One chip cell per dimension */}
                {DIMENSION_LABELS.map((dim) => {
                  const cellStatuses: Record<string, string> = {};
                  topic.codes.forEach((code) => {
                    const s = matrix[cat]?.[dim.key]?.[code];
                    if (s) cellStatuses[code] = s;
                  });
                  const status = aggregateCellStatus(cellStatuses);
                  return (
                    <div
                      key={dim.key}
                      style={{
                        display: "flex",
                        justifyContent: "center",
                        alignItems: "center",
                        padding: "8px",
                        borderBottom: "1px solid #f0f0f0",
                      }}
                    >
                      <StatusChip status={status} />
                    </div>
                  );
                })}
              </React.Fragment>
            ))}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

// ---- Recommendation maps --------------------------------------------------

const MAMI_CODE_TO_REC_ID: Record<string, string> = {
  "S-HRA-1.1": "HRA-1.1", "S-MRA-1.1": "MRA-1.1", "S-TA-1.1": "TA-1.1",
  "S-HRA-2.1": "HRA-1.2", "S-MRA-2.1": "MRA-1.2", "S-TA-2.1": "TA-1.2",
  "S-HRA-3.1": "HRA-1.3", "S-MRA-3.1": "MRA-1.3", "S-TA-3.1": "TA-1.3",
  "PM-HRA-1.1": "HRA-2.1", "PM-MRA-1.1": "MRA-2.1", "PM-TA-1.1": "TA-2.1",
  "PM-HRA-2.1": "HRA-2.2", "PM-MRA-2.1": "MRA-2.2", "PM-TA-2.1": "TA-2.2",
  "D-HRA-1.1": "HRA-3.1", "D-MRA-1.1": "MRA-3.1", "D-TA-1.1": "TA-3.1",
  "D-HRA-2.1": "HRA-3.2", "D-MRA-2.1": "MRA-3.2", "D-TA-2.1": "TA-3.2",
  "SER-HRA-1.1": "HRA-4.1", "SER-MRA-1.1": "MRA-4.1", "SER-TA-1.1": "TA-4.1",
  "SER-HRA-2.1": "HRA-4.2", "SER-MRA-2.1": "MRA-4.2", "SER-TA-2.1": "TA-4.2",
};

const MAMI_CODE_TO_LABELS: Record<string, { dimension_label: string; topic_label: string }> = {
  "S-HRA-1.1":  { dimension_label: "Human Readable/Actionable", topic_label: "Scheme publication & updates" },
  "S-MRA-1.1":  { dimension_label: "Machine Readable",          topic_label: "Scheme publication & updates" },
  "S-TA-1.1":   { dimension_label: "Trust Anchors",             topic_label: "Scheme publication & updates" },
  "S-HRA-2.1":  { dimension_label: "Human Readable/Actionable", topic_label: "Incidents & dispute management" },
  "S-MRA-2.1":  { dimension_label: "Machine Readable",          topic_label: "Incidents & dispute management" },
  "S-TA-2.1":   { dimension_label: "Trust Anchors",             topic_label: "Incidents & dispute management" },
  "S-HRA-3.1":  { dimension_label: "Human Readable/Actionable", topic_label: "Traceability" },
  "S-MRA-3.1":  { dimension_label: "Machine Readable",          topic_label: "Traceability" },
  "S-TA-3.1":   { dimension_label: "Trust Anchors",             topic_label: "Traceability" },
  "PM-HRA-1.1": { dimension_label: "Human Readable/Actionable", topic_label: "On(off)-boarding" },
  "PM-MRA-1.1": { dimension_label: "Machine Readable",          topic_label: "On(off)-boarding" },
  "PM-TA-1.1":  { dimension_label: "Trust Anchors",             topic_label: "On(off)-boarding" },
  "PM-HRA-2.1": { dimension_label: "Human Readable/Actionable", topic_label: "Participants discovery" },
  "PM-MRA-2.1": { dimension_label: "Machine Readable",          topic_label: "Participants discovery" },
  "PM-TA-2.1":  { dimension_label: "Trust Anchors",             topic_label: "Participants discovery" },
  "D-HRA-1.1":  { dimension_label: "Human Readable/Actionable", topic_label: "Data(sets) Publication & discovery" },
  "D-MRA-1.1":  { dimension_label: "Machine Readable",          topic_label: "Data(sets) Publication & discovery" },
  "D-TA-1.1":   { dimension_label: "Trust Anchors",             topic_label: "Data(sets) Publication & discovery" },
  "D-HRA-2.1":  { dimension_label: "Human Readable/Actionable", topic_label: "Data(sets) Provisions" },
  "D-MRA-2.1":  { dimension_label: "Machine Readable",          topic_label: "Data(sets) Provisions" },
  "D-TA-2.1":   { dimension_label: "Trust Anchors",             topic_label: "Data(sets) Provisions" },
  "SER-HRA-1.1":{ dimension_label: "Human Readable/Actionable", topic_label: "Services Publications and discovery" },
  "SER-MRA-1.1":{ dimension_label: "Machine Readable",          topic_label: "Services Publications and discovery" },
  "SER-TA-1.1": { dimension_label: "Trust Anchors",             topic_label: "Services Publications and discovery" },
  "SER-HRA-2.1":{ dimension_label: "Human Readable/Actionable", topic_label: "Services Provisions" },
  "SER-MRA-2.1":{ dimension_label: "Machine Readable",          topic_label: "Services Provisions" },
  "SER-TA-2.1": { dimension_label: "Trust Anchors",             topic_label: "Services Provisions" },
};

const RECOMMENDATIONS: Record<string, string> = {
  "HRA-1.1": "Unless highly sensitive, please consider making your scheme agreements publicly available.",
  "MRA-1.1": "Please consider publishing your scheme in a machine-readable format by having an actionable sandbox/demo for end-users to interact with.",
  "TA-1.1":  "Please consider specifying the actor responsible for publishing and updating the scheme, and also specify allowed procedures/actions that the scheme authority can conduct for updating and publishing the scheme.",
  "HRA-1.2": "Please consider including conditions in the scheme agreement via various clauses, like settlement clauses, liability clauses or any force majeure clauses.",
  "MRA-1.2": "Please consider supporting an automatic way for flagging incidents and an automatic way to track progress of the started disputes.",
  "TA-1.2":  "Please consider indicating what are the trust anchor(s) that parties can go to for dispute management.",
  "HRA-1.3": "Please consider providing traceability tools generating a human readable/actionable record that can be used to achieve legal clarity for any subsequent dispute handling.",
  "MRA-1.3": "Please consider providing traceability tools generating a machine readable/actionable record that can be used to achieve automatic flagging of incidents and aid in subsequent dispute handling.",
  "TA-1.3":  "Please consider specifying a Trust Anchor responsible for the operation/provision of the traceability tools. Also, please consider specifying what is being traced in accordance with the scope of your scheme, to ensure clarity and transparency for the interacting participants and/or 3rd parties joining the scheme.",
  "HRA-2.1": "Please consider providing human readable/actionable information regarding your scheme participation, including onboarding and offboarding procedures (to the extent allowed by privacy & sensitivity conditions).",
  "MRA-2.1": "Please consider providing code/APIs and/or adjacent testbeds to technically support onboarding and offboarding procedures. Also, please consider to what extent you may publicly disclose the scheme participation, onboarding procedures and access to testbeds. Also, please consider having access management controls in place for any sensitive content, including clear access conditions.",
  "TA-2.1":  "Please consider specifying trust anchors for onboarding and offboarding procedures.",
  "HRA-2.2": "Please consider providing information about existing participants of the scheme via a registry, with access rights limited by sensitivity conditions of the scheme.",
  "MRA-2.2": "Please consider providing a machine readable/actionable registry of participant endpoints.",
  "TA-2.2":  "Please consider specifying Trust Anchors for registry services provision.",
  "HRA-3.1": "Please consider providing at least general information regarding data sets available to scheme participants to discover, understand, access and/or visit said data to the extent permitted by sensitivity & privacy conditions, and consider providing explicit descriptions about the access conditions. Also, please consider adhering to the FAIR principles.",
  "MRA-3.1": "Please consider ensuring that your member provide information about data/data sets in a machine readable/actionable way, enabling other participants to discover, understand, access and/or visit said data, under specific sensitivity & privacy conditions.",
  "TA-3.1":  "Please consider specifying trust anchors used for metadata standards, and specifying trust anchors/credibility means for assurance in data characteristics relevant in the context.",
  "HRA-3.2": "Please consider NOT providing actual data UNLESS the specified access & usage conditions are met; these conditions should then be documented in a human readable/actionable form.",
  "MRA-3.2": "Please consider NOT providing actual data UNLESS the specified access & usage conditions are met AND during a request for data access/visiting an automatic (machine readable/actionable) procedure of authentication & authorization has been properly completed.",
  "TA-3.2":  "Please consider specifying the Scheme Authority and/or governance mechanisms/procedures as a trust anchor to ensure participants have obtained trusted digital identity means for relying parties to use for authenticating & authorizing to provide data access.",
  "HRA-4.1": "Please consider providing (at least general) information regarding services available to the scheme participants and/or 3rd parties (to the extent permitted by sensitivity & privacy conditions).",
  "MRA-4.1": "Please consider ensuring you and/or your participants provide (at least general) information regarding services available to other participants and/or 3rd parties in a machine readable/actionable way (to the extent permitted by sensitivity & privacy conditions).",
  "TA-4.1":  "Please consider specifying Trust Anchors for each service provided under the scheme.",
  "HRA-4.2": "Please consider NOT providing actual services UNLESS the specified provision conditions are met; such conditions should then be made human readable/actionable.",
  "MRA-4.2": "Please consider NOT providing actual services UNLESS the specified provision conditions are met and any automatic checks to authorize the provision of service are completed.",
  "TA-4.2":  "Please consider establishing Scheme Authority and/or governance mechanisms & procedures to ensure that trusted service providers adhere to the scheme conditions.",
};

// ---- Next steps panel -----------------------------------------------------

const NEXT_STEPS = [
  "Review your results",
  "Discuss with an expert",
  "Define improvement priorities",
  "Create improvement plan",
];

function NextStepsPanel({ onDownload, isDownloading }: { onDownload: () => void; isDownloading: boolean }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <h2
        style={{
          fontFamily: "'Rubik', sans-serif",
          fontWeight: 600,
          fontSize: "1.25rem",
          color: "#06004f",
          margin: 0,
        }}
      >
        Next steps
      </h2>

      <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
        {NEXT_STEPS.map((step, idx) => (
          <div key={idx} style={{ display: "flex", alignItems: "flex-start", gap: "14px" }}>
            <div
              style={{
                width: "32px",
                height: "32px",
                minWidth: "32px",
                borderRadius: "50%",
                background: "#06004f",
                color: "white",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: "'Rubik', sans-serif",
                fontWeight: 600,
                fontSize: "0.875rem",
              }}
            >
              {idx + 1}
            </div>
            <p
              style={{
                fontFamily: "'Rubik', sans-serif",
                fontSize: "0.95rem",
                color: "#06004f",
                margin: 0,
                paddingTop: "6px",
                lineHeight: 1.4,
              }}
            >
              {step}
            </p>
          </div>
        ))}
      </div>

      <div style={{ marginTop: "8px", display: "flex", flexDirection: "column", gap: "10px" }}>
        <Button
          type="primary"
          size="large"
          loading={isDownloading}
          disabled={isDownloading}
          onClick={onDownload}
          style={{
            borderRadius: "8px",
            fontFamily: "'Rubik', sans-serif",
            fontWeight: 600,
            width: "100%",
          }}
        >
          Download results as PDF
        </Button>
        <a
          href="mailto:info@coe-dsc.nl?subject=MAMI%20Checker%20Results"
          style={{
            display: "block",
            textAlign: "center",
            padding: "10px 0",
            borderRadius: "8px",
            border: "1px solid #06004f",
            fontFamily: "'Rubik', sans-serif",
            fontWeight: 500,
            fontSize: "0.95rem",
            color: "#06004f",
            textDecoration: "none",
          }}
        >
          Contact us about your results
        </a>
        <p style={{
          fontFamily: "'Rubik', sans-serif",
          fontSize: "0.8rem",
          color: "rgba(6,0,79,0.6)",
          marginTop: "4px",
          textAlign: "center",
        }}>
          Our experts will help you translate your results into concrete actions
        </p>
      </div>
    </div>
  );
}

// ---- Main page ------------------------------------------------------------

function ReportPage() {
  const screens = useBreakpoint();
  const isMobile = screens.md === false;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ReportData | null>(null);
  const [initiativeId, setInitiativeId] = useState<number | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  // Single merged effect — fires on every mount (no stale initiativeId dependency)
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    api.get<{ id: number; name: string; status: string }>("/initiatives/me")
      .then((res) => {
        if (cancelled) return;
        const id = res.data.id;
        setInitiativeId(id);
        return api.post<ReportData>(`/initiatives/${id}/report/data`, {});
      })
      .then((res) => {
        if (cancelled || !res) return;
        setData(res.data);
      })
      .catch(() => {
        if (!cancelled) setError("Failed to generate report. Make sure you have answered the questionnaire.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, []);

  const recommendations = data
    ? Object.keys(MAMI_CODE_TO_REC_ID).filter(code => {
        const answer = data.answers.find((a: { mami_code: string; answer_value: string }) => a.mami_code === code);
        return !answer || answer.answer_value === "NOT_THERE_YET";
      }).map(code => {
        const recId = MAMI_CODE_TO_REC_ID[code];
        const labels = MAMI_CODE_TO_LABELS[code];
        return {
          code,
          dimension_label: labels?.dimension_label ?? code,
          topic_label: labels?.topic_label ?? "",
          text: RECOMMENDATIONS[recId] ?? "",
        };
      }).filter(r => r.text)
    : [];

  const handleDownload = async () => {
    if (!initiativeId) return;
    setIsDownloading(true);
    setDownloadError(null);
    try {
      const token = localStorage.getItem('mami_access_token');
      const res = await fetch(
        `${import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'}/initiatives/${initiativeId}/report/pdf`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setDownloadError((body as { detail?: string }).detail ?? 'Failed to generate PDF. Please try again.');
      } else {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'MAMI-Interoperability-Report.pdf';
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch {
      setDownloadError('Network error. Please try again.');
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div
      style={{
        padding: "2rem",
        background: "rgba(57,158,90,0.08)",
        minHeight: "100vh",
      }}
    >
      <h1
        style={{
          fontFamily: "'Rubik', sans-serif",
          fontWeight: 500,
          fontSize: "35px",
          color: "#06004f",
          marginBottom: "2rem",
        }}
      >
        MAMI Interoperability heatmap
      </h1>

      {loading && (
        <div style={{ display: "flex", justifyContent: "center", paddingTop: "4rem" }}>
          <Spin size="large" />
        </div>
      )}

      {!loading && error && (
        <Alert
          type="error"
          message={error}
          showIcon
          style={{ maxWidth: "600px" }}
        />
      )}

      {!loading && data && (
        <>
          <p
            style={{
              fontFamily: "'Rubik', sans-serif",
              fontSize: "0.875rem",
              color: "rgba(6,0,79,0.55)",
              marginBottom: "1.5rem",
            }}
          >
            Initiative: <strong style={{ color: "#06004f" }}>{data.initiative.name}</strong>
            {data.initiative.generated_at && (
              <span style={{ marginLeft: "1rem" }}>
                Generated: {new Date(data.initiative.generated_at).toLocaleString()}
              </span>
            )}
          </p>

          <div
            style={{
              display: "flex",
              gap: "24px",
              alignItems: "flex-start",
              flexWrap: "wrap",
            }}
          >
            {/* Left: Heatmap card */}
            <div
              style={{
                flex: "2 1 520px",
                background: "white",
                borderRadius: "16px",
                overflow: "visible",
                boxShadow: "0 2px 12px rgba(6,0,79,0.08)",
              }}
            >
              <div style={{ padding: "1.5rem 1.5rem 0" }}>
                <h2
                  style={{
                    fontFamily: "'Rubik', sans-serif",
                    fontWeight: 600,
                    fontSize: "1.1rem",
                    color: "#06004f",
                    marginBottom: "1rem",
                  }}
                >
                  Interoperability heatmap
                </h2>
              </div>
              <div style={{ overflowX: "auto" }}>
                <HeatmapMatrix matrix={data.matrix as unknown as ReportMatrix} topicStructure={data.topic_structure} isMobile={isMobile} />
              </div>
              <div style={{ padding: "1rem 1.5rem" }}>
                <div
                  style={{
                    display: "flex",
                    gap: "16px",
                    flexWrap: "wrap",
                    marginTop: "0.5rem",
                  }}
                >
                  {[
                    { status: "yes", label: "Compliant" },
                    { status: "not_yet", label: "In progress" },
                    { status: "n_a", label: "Not applicable" },
                  ].map(({ status, label }) => (
                    <div
                      key={status}
                      style={{ display: "flex", alignItems: "center", gap: "8px" }}
                    >
                      <StatusChip status={status} />
                      <span
                        style={{
                          fontFamily: "'Rubik', sans-serif",
                          fontSize: "0.8rem",
                          color: "rgba(6,0,79,0.6)",
                        }}
                      >
                        = {label}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Right: Next steps card */}
            <div
              style={{
                flex: "1 1 280px",
                background: "#cfe7d6",
                borderRadius: "16px",
                padding: "1.5rem",
              }}
            >
              <NextStepsPanel onDownload={handleDownload} isDownloading={isDownloading} />
              {downloadError && (
                <Alert type="error" message={downloadError} showIcon style={{ marginTop: "12px" }} />
              )}
            </div>
          </div>

          {recommendations.length > 0 && (
            <div style={{ marginTop: "24px" }}>
              <Collapse
                defaultActiveKey={[]}
                items={[
                  {
                    key: "recommendations",
                    label: (
                      <span style={{ fontFamily: "'Rubik', sans-serif", fontWeight: 600, color: "#06004f", fontSize: "1rem" }}>
                        Recommendations for improving your interoperability
                      </span>
                    ),
                    children: (
                      <div style={{ display: "flex", flexDirection: "column", gap: "0" }}>
                        <p style={{ fontFamily: "'Rubik', sans-serif", fontSize: "0.875rem", color: "#333", marginBottom: "16px", lineHeight: 1.6 }}>
                          Below are suggested steps you could take in the areas that you have indicated as 'Not yet, but planning to do'. The MAMI document, available on the CoE-DSC website, contains elaborate recommendations for all of the areas.
                        </p>
                        {recommendations.map((r, idx) => (
                          <div
                            key={r.code}
                            style={{
                              padding: "12px 0",
                              borderTop: idx === 0 ? "none" : "1px solid rgba(6,0,79,0.08)",
                            }}
                          >
                            <p style={{ fontFamily: "'Rubik', sans-serif", fontSize: "0.875rem", color: "#06004f", margin: 0, lineHeight: 1.6 }}>
                              <strong>{r.dimension_label} — {r.topic_label}</strong>
                              {" - "}
                              {r.text}
                            </p>
                          </div>
                        ))}
                      </div>
                    ),
                  },
                ]}
                style={{ borderRadius: "16px", background: "white", boxShadow: "0 2px 12px rgba(6,0,79,0.08)" }}
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}

import { createFileRoute, useSearch } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Button, Spin, Alert } from "antd";
import { api } from "../../lib/api";
import { fetchReportData, type ReportContract } from "../../lib/reports";

export const Route = createFileRoute("/_app/report")({
  component: ReportPage,
});

// ---- Search params ----------------------------------------------------------
// D-04: optional initiative_id + assessment_id read from the URL — supports
// both the owner's own report (no params) and admin/history deep-links.
// No validateSearch is registered on this route (mirrors the existing
// `/_auth/login` precedent — loosely typed search, cast at the read site)
// so an arbitrary extra query param never breaks navigation.

function useReportSearchParams(): { initiativeId?: number; assessmentId?: number } {
  const search = useSearch({ from: "/_app/report" }) as Record<string, string | undefined>;
  const initiativeId = search.initiative_id ? Number(search.initiative_id) : undefined;
  const assessmentId = search.assessment_id ? Number(search.assessment_id) : undefined;
  return {
    initiativeId: Number.isFinite(initiativeId) ? initiativeId : undefined,
    assessmentId: Number.isFinite(assessmentId) ? assessmentId : undefined,
  };
}

// ---- Priority list row -------------------------------------------------------

function PriorityRow({
  item,
}: {
  item: ReportContract["priority_list"][number];
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "16px",
        padding: "12px 0",
        borderBottom: "1px solid rgba(6,0,79,0.08)",
      }}
    >
      <span
        aria-hidden
        style={{
          width: "12px",
          height: "12px",
          minWidth: "12px",
          borderRadius: "50%",
          background: item.band_color,
          display: "inline-block",
        }}
      />
      <span
        style={{
          flex: "1 1 auto",
          fontFamily: "'Rubik', sans-serif",
          fontSize: "14px",
          fontWeight: 400,
          color: "#008ecf",
          whiteSpace: "normal",
        }}
      >
        {item.name}
      </span>
      <span
        style={{
          fontFamily: "'Rubik', sans-serif",
          fontSize: "13px",
          fontWeight: 400,
          color: "rgba(6,0,79,0.6)",
          whiteSpace: "nowrap",
        }}
      >
        {item.band_label}
      </span>
      <span
        style={{
          fontFamily: "'Rubik', sans-serif",
          fontSize: "14px",
          fontWeight: 600,
          color: "#008ecf",
          minWidth: "48px",
          textAlign: "right",
        }}
      >
        {item.score.toFixed(2)}
      </span>
    </div>
  );
}

// ---- Main page ----------------------------------------------------------------

function ReportPage() {
  const { initiativeId: initiativeIdParam, assessmentId } = useReportSearchParams();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ReportContract | null>(null);
  const [resolvedInitiativeId, setResolvedInitiativeId] = useState<number | null>(
    initiativeIdParam ?? null,
  );
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    let cancelled = false;

    const resolveInitiativeId: Promise<number> = initiativeIdParam
      ? Promise.resolve(initiativeIdParam)
      : api.get<{ id: number }>("/initiatives/me").then((res) => res.data.id);

    resolveInitiativeId
      .then((id) => {
        if (cancelled) return undefined;
        setResolvedInitiativeId(id);
        return fetchReportData(id, assessmentId);
      })
      .then((contract) => {
        if (cancelled || !contract) return;
        setData(contract);
      })
      .catch(() => {
        if (!cancelled) {
          setError(
            "We couldn't load this report. Make sure the assessment has been fully submitted, then try again.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [initiativeIdParam, assessmentId, retryToken]);

  const handleRetry = () => {
    setLoading(true);
    setError(null);
    setRetryToken((t) => t + 1);
  };

  const handleDownload = async () => {
    if (!resolvedInitiativeId) return;
    setIsDownloading(true);
    setDownloadError(null);
    try {
      const token = localStorage.getItem("mami_access_token");
      const url = new URL(
        `${api.defaults.baseURL}/initiatives/${resolvedInitiativeId}/report/pdf`,
      );
      if (assessmentId) url.searchParams.set("assessment_id", String(assessmentId));
      const res = await fetch(url.toString(), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setDownloadError((body as { detail?: string }).detail ?? "Failed to generate PDF. Please try again.");
      } else {
        const blob = await res.blob();
        const blobUrl = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = blobUrl;
        a.download = "DSSC-Maturity-Report.pdf";
        a.click();
        URL.revokeObjectURL(blobUrl);
      }
    } catch {
      setDownloadError("Network error. Please try again.");
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div
      style={{
        padding: "32px",
        background: "rgba(57,158,90,0.08)",
        minHeight: "100vh",
      }}
    >
      <h1
        style={{
          fontFamily: "'Rubik', sans-serif",
          fontWeight: 600,
          fontSize: "28px",
          color: "#008ecf",
          marginBottom: "32px",
        }}
      >
        Your DSSC Maturity Report
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
          action={
            <Button size="small" onClick={handleRetry}>
              Retry
            </Button>
          }
          style={{ maxWidth: "600px" }}
        />
      )}

      {!loading && !error && data && (
        <>
          <p
            style={{
              fontFamily: "'Rubik', sans-serif",
              fontSize: "14px",
              color: "rgba(6,0,79,0.6)",
              marginBottom: "24px",
            }}
          >
            Initiative: <strong style={{ color: "#008ecf" }}>{data.initiative.name}</strong>
          </p>

          <div
            style={{
              display: "flex",
              gap: "24px",
              alignItems: "flex-start",
              flexWrap: "wrap",
            }}
          >
            {/* Radar chart card — primary visual anchor (UI-SPEC Dimension 2) */}
            <div
              style={{
                flex: "3 1 480px",
                background: "#ffffff",
                borderRadius: "16px",
                boxShadow: "0 2px 12px rgba(6,0,79,0.08)",
                padding: "24px",
              }}
            >
              <h2
                style={{
                  fontFamily: "'Rubik', sans-serif",
                  fontWeight: 600,
                  fontSize: "20px",
                  color: "#008ecf",
                  marginBottom: "16px",
                }}
              >
                Maturity radar
              </h2>
              {/* RPRT-01/D-02: server-generated SVG rendered verbatim — no
                  client-side polygon math, no client-side band re-derivation. */}
              <div
                style={{ display: "flex", justifyContent: "center" }}
                dangerouslySetInnerHTML={{ __html: data.radar_chart_svg }}
              />
            </div>

            {/* Priority list card — secondary */}
            <div
              style={{
                flex: "2 1 360px",
                background: "#ffffff",
                borderRadius: "16px",
                boxShadow: "0 2px 12px rgba(6,0,79,0.08)",
                padding: "24px",
              }}
            >
              <h2
                style={{
                  fontFamily: "'Rubik', sans-serif",
                  fontWeight: 600,
                  fontSize: "20px",
                  color: "#008ecf",
                  marginBottom: "16px",
                }}
              >
                Priority areas
              </h2>
              <div>
                {data.priority_list.map((item) => (
                  <PriorityRow key={item.category_id} item={item} />
                ))}
              </div>
            </div>
          </div>

          <div style={{ marginTop: "32px" }}>
            <Button
              type="primary"
              size="large"
              loading={isDownloading}
              disabled={isDownloading}
              onClick={handleDownload}
              style={{
                borderRadius: "8px",
                fontFamily: "'Rubik', sans-serif",
                fontWeight: 600,
              }}
            >
              Download PDF Report
            </Button>
            {downloadError && (
              <Alert type="error" message={downloadError} showIcon style={{ marginTop: "12px", maxWidth: "600px" }} />
            )}
          </div>
        </>
      )}
    </div>
  );
}

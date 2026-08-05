import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Card, Table, Button, Alert, Skeleton } from "antd";
import type { ColumnsType } from "antd/es/table";
import { api } from "../../lib/api";
import { fetchAssessmentHistory, type AssessmentSummary } from "../../lib/assessments";

export const Route = createFileRoute("/_app/assessments")({
  component: AssessmentsPage,
});

// ─── Types ────────────────────────────────────────────────────────────────────

interface CurrentInitiative {
  id: number;
  name: string;
}

// ─── AssessmentsPage ────────────────────────────────────────────────────────────

function AssessmentsPage() {
  // Step 1: resolve the current user's initiative id — the history endpoint
  // is scoped to a specific initiative, ownership re-derived server-side
  // (T-15-04). This page only ever requests the current user's own
  // initiative, never an arbitrary id.
  const {
    data: initiative,
    isLoading: initiativeLoading,
    isError: initiativeError,
    refetch: refetchInitiative,
  } = useQuery<CurrentInitiative>({
    queryKey: ["current-initiative"],
    queryFn: async () => {
      const res = await api.get<CurrentInitiative>("/initiatives/me");
      return res.data;
    },
  });

  // Step 2: fetch this initiative's submitted-assessment history.
  const {
    data: history,
    isLoading: historyLoading,
    isError: historyError,
    refetch: refetchHistory,
  } = useQuery<AssessmentSummary[]>({
    queryKey: ["assessment-history", initiative?.id],
    queryFn: () => fetchAssessmentHistory(initiative!.id),
    enabled: !!initiative?.id,
  });

  const isLoading = initiativeLoading || (!!initiative?.id && historyLoading);
  const isError = initiativeError || historyError;

  const handleRetry = () => {
    void refetchInitiative();
    if (initiative?.id) void refetchHistory();
  };

  // ─── Version-list table ──────────────────────────────────────────────────

  const versionColumns: ColumnsType<AssessmentSummary> = [
    {
      title: "Submitted",
      dataIndex: "submitted_at",
      key: "submitted_at",
      render: (v: string) => (v ? new Date(v).toLocaleDateString() : "—"),
    },
    {
      title: "Version",
      dataIndex: "version",
      key: "version",
      render: (v: number) => `v${v}`,
    },
    {
      title: "Overall average",
      dataIndex: "overall_average",
      key: "overall_average",
      render: (v: number) => v.toFixed(2),
    },
    {
      title: "Report",
      key: "report",
      render: (_: unknown, record: AssessmentSummary) => (
        <Link to="/report" search={{ assessment_id: record.id }}>
          View report
        </Link>
      ),
    },
  ];

  // ─── Comparison table (pivot dimension_scores across versions) ──────────

  const dimensionNames: string[] =
    history && history.length > 0
      ? history[0].dimension_scores.map((d) => d.name)
      : [];

  interface ComparisonRow {
    key: string;
    dimension: string;
    [versionColumnKey: string]: string | number;
  }

  const comparisonRows: ComparisonRow[] = dimensionNames.map((name, idx) => {
    const row: ComparisonRow = { key: `dim-${idx}`, dimension: name };
    (history ?? []).forEach((a) => {
      const match = a.dimension_scores.find((d) => d.name === name);
      row[`v${a.version}`] = match ? match.score.toFixed(2) : "—";
    });
    return row;
  });

  const comparisonColumns: ColumnsType<ComparisonRow> = [
    {
      title: "Dimension",
      dataIndex: "dimension",
      key: "dimension",
      fixed: "left",
      width: 220,
    },
    ...(history ?? []).map((a) => ({
      title: `v${a.version}`,
      dataIndex: `v${a.version}`,
      key: `v${a.version}`,
      width: 120,
    })),
  ];

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto" }}>
      <h1
        style={{
          fontSize: "1.75rem",
          fontWeight: 700,
          color: "#008ecf",
          marginBottom: "1.5rem",
          fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
        }}
      >
        Assessment History
      </h1>

      {isError && (
        <Alert
          type="error"
          message="Couldn't load your assessment history."
          action={
            <Button size="small" onClick={handleRetry}>
              Retry
            </Button>
          }
          style={{ marginBottom: "1.5rem" }}
          showIcon
        />
      )}

      {!isError && isLoading && (
        <Card style={{ borderRadius: "0", boxShadow: "0 2px 12px rgba(0,142,207,0.06)" }}>
          <Skeleton active paragraph={{ rows: 4 }} />
        </Card>
      )}

      {!isError && !isLoading && history && history.length === 0 && (
        <Card style={{ borderRadius: "0", boxShadow: "0 2px 12px rgba(0,142,207,0.06)" }}>
          <h2
            style={{
              fontSize: "1.25rem",
              fontWeight: 600,
              color: "#008ecf",
              margin: 0,
              fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
            }}
          >
            No completed assessments yet
          </h2>
          <p
            style={{
              fontSize: "0.875rem",
              color: "rgba(0,142,207,0.6)",
              marginTop: "0.5rem",
              fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
            }}
          >
            Finish your first dataspace maturity assessment to see it appear here as your first version.
          </p>
        </Card>
      )}

      {!isError && !isLoading && history && history.length > 0 && (
        <>
          <Card
            style={{
              borderRadius: "0",
              boxShadow: "0 2px 12px rgba(0,142,207,0.06)",
              marginBottom: "1.5rem",
            }}
          >
            <h2
              style={{
                fontSize: "1.25rem",
                fontWeight: 600,
                color: "#008ecf",
                marginBottom: "1rem",
                fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
              }}
            >
              Your assessment history ({history.length})
            </h2>
            <Table
              dataSource={history}
              columns={versionColumns}
              rowKey="id"
              pagination={{ pageSize: 10, showSizeChanger: false }}
              size="small"
              style={{ borderRadius: "8px", overflow: "hidden" }}
            />
          </Card>

          <Card
            style={{
              borderRadius: "0",
              boxShadow: "0 2px 12px rgba(0,142,207,0.06)",
            }}
          >
            <h2
              style={{
                fontSize: "1.25rem",
                fontWeight: 600,
                color: "#008ecf",
                marginBottom: "1rem",
                fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
              }}
            >
              Compare scores across versions
            </h2>
            <div style={{ overflowX: "auto" }}>
              <Table
                dataSource={comparisonRows}
                columns={comparisonColumns}
                rowKey="key"
                pagination={false}
                size="small"
                scroll={{ x: "max-content" }}
                style={{ borderRadius: "8px", overflow: "hidden" }}
              />
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

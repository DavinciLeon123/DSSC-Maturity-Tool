import { createFileRoute, redirect, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { Card, Spin, Alert, Button, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { api } from "../../lib/api";

const { Title, Text } = Typography;

export const Route = createFileRoute("/_app/admin/heatmap")({
  beforeLoad: async () => {
    try {
      const res = await api.get<{ role: string }>("/auth/me");
      if (res.data.role !== "ADMIN") {
        throw redirect({ to: "/dashboard" });
      }
    } catch (err: unknown) {
      // Rethrow redirect errors; swallow auth errors (redirect to dashboard)
      if (err && typeof err === "object" && "to" in err) throw err;
      throw redirect({ to: "/dashboard" });
    }
  },
  component: AdminHeatmapPage,
});

// ---- Types ------------------------------------------------------------------
// Mirrors backend/app/api/v1/admin.py's AdminAggregateResponse/
// AdminInitiativeAggregateRow verbatim (ADMN-01).

interface DimensionScore {
  category_id: string;
  name: string;
  score: number;
}

interface AdminInitiativeAggregateRow {
  id: number;
  name: string;
  report_assessment_id: number | null;
  dimension_scores: DimensionScore[] | null;
  overall_average: number | null;
  has_data: boolean;
}

interface AdminAggregateResponse {
  org_average_scores: DimensionScore[];
  org_radar_chart_svg: string | null;
  initiatives: AdminInitiativeAggregateRow[];
}

// ---- AdminHeatmapPage component -----------------------------------------------

export function AdminHeatmapPage() {
  const [data, setData] = useState<AdminAggregateResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    api
      .get<AdminAggregateResponse>("/admin/heatmap")
      .then((res) => {
        if (!cancelled) setData(res.data);
      })
      .catch(() => {
        if (!cancelled) setError("Couldn't load the aggregated maturity data.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [retryToken]);

  const handleRetry = () => {
    setLoading(true);
    setError(null);
    setRetryToken((t) => t + 1);
  };

  // D-08: never re-derive band color/label from a raw score client-side —
  // this page only ever displays the raw dimension_scores/overall_average
  // numbers the backend computed; no maturity-band rendering happens here
  // (that is report.tsx's job, per-initiative, not the admin aggregate).

  const submittedCount = data ? data.initiatives.filter((i) => i.has_data).length : 0;
  const isOrgEmpty = !!data && data.org_radar_chart_svg === null;

  const dimensionColumns: { category_id: string; name: string }[] = data
    ? data.org_average_scores.map((d) => ({ category_id: d.category_id, name: d.name }))
    : [];

  const columns: ColumnsType<AdminInitiativeAggregateRow> = [
    {
      title: "Initiative",
      dataIndex: "name",
      key: "name",
      ellipsis: true,
      width: 220,
    },
    ...dimensionColumns.map(({ category_id, name }) => ({
      title: name,
      key: `dim-${category_id}`,
      width: 140,
      render: (_: unknown, record: AdminInitiativeAggregateRow) => {
        // Match on the stable `category_id`, not the mutable display
        // `name` (WR-01) — `record.dimension_scores` is a per-initiative
        // frozen snapshot (per CR-01) that may use a different name for the
        // same category id than the current live config does.
        const match = record.dimension_scores?.find((d) => d.category_id === category_id);
        return match ? match.score.toFixed(2) : "—";
      },
    })),
    {
      title: "Overall average",
      dataIndex: "overall_average",
      key: "overall_average",
      width: 140,
      render: (v: number | null) => (v != null ? v.toFixed(2) : "—"),
    },
    {
      title: "Report",
      key: "report",
      width: 140,
      render: (_: unknown, record: AdminInitiativeAggregateRow) =>
        record.has_data && record.report_assessment_id != null ? (
          <Link
            to="/report"
            search={{ initiative_id: record.id, assessment_id: record.report_assessment_id }}
          >
            View report
          </Link>
        ) : (
          <Tag color="default">No data yet</Tag>
        ),
    },
  ];

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "2rem" }}>
      {/* Back link */}
      <div style={{ marginBottom: "1rem" }}>
        <Link to="/admin">
          <Button
            type="default"
            style={{ fontFamily: "'Rubik', sans-serif", fontWeight: 500 }}
          >
            &larr; Back to Admin
          </Button>
        </Link>
      </div>

      <Title
        level={1}
        style={{
          fontFamily: "'Rubik', sans-serif",
          fontWeight: 600,
          color: "#06004f",
          marginBottom: "1.5rem",
          fontSize: "28px",
        }}
      >
        Aggregated Maturity Overview
      </Title>

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
          {/* Org radar card (or its empty-state) — primary visual anchor
              (UI-SPEC Dimension 2). WR-02: the "no submitted assessments
              yet" messaging is scoped to this card only — it must not hide
              the per-initiative table below, which the backend populates
              (including has_data=False rows) even when the org-wide radar
              is suppressed. */}
          {isOrgEmpty ? (
            <Card
              style={{
                borderRadius: "16px",
                boxShadow: "0 2px 12px rgba(6,0,79,0.08)",
                marginBottom: "1.5rem",
              }}
            >
              <Title
                level={2}
                style={{ fontFamily: "'Rubik', sans-serif", fontWeight: 600, color: "#06004f", fontSize: "20px", marginBottom: "0.5rem" }}
              >
                No submitted assessments yet
              </Title>
              <Text style={{ fontFamily: "'Rubik', sans-serif", fontSize: "14px", color: "rgba(6,0,79,0.6)" }}>
                Once an initiative fully completes and submits the questionnaire, its scores will appear here.
              </Text>
            </Card>
          ) : (
            <Card
              style={{
                borderRadius: "16px",
                boxShadow: "0 2px 12px rgba(6,0,79,0.08)",
                marginBottom: "1.5rem",
              }}
            >
              <Title
                level={2}
                style={{ fontFamily: "'Rubik', sans-serif", fontWeight: 600, color: "#06004f", fontSize: "20px", marginBottom: "1rem" }}
              >
                Org-wide maturity radar
              </Title>
              <div
                style={{ display: "flex", justifyContent: "center" }}
                dangerouslySetInnerHTML={{ __html: data.org_radar_chart_svg ?? "" }}
              />
              <Text
                style={{
                  fontFamily: "'Rubik', sans-serif",
                  fontSize: "13px",
                  color: "rgba(6,0,79,0.6)",
                  display: "block",
                  marginTop: "1rem",
                }}
              >
                Based on <strong style={{ color: "#06004f" }}>{submittedCount}</strong> submitted
                initiative{submittedCount !== 1 ? "s" : ""}.
              </Text>
            </Card>
          )}

          {/* Per-initiative table — always rendered, regardless of
              org-wide radar state (WR-02); handles has_data=False rows via
              the "No data yet" tag. */}
          <Card style={{ borderRadius: "16px", boxShadow: "0 2px 12px rgba(6,0,79,0.08)" }}>
            <Title
              level={2}
              style={{ fontFamily: "'Rubik', sans-serif", fontWeight: 600, color: "#06004f", fontSize: "20px", marginBottom: "1rem" }}
            >
              Per-initiative breakdown
            </Title>
            <Table
              dataSource={data.initiatives}
              columns={columns}
              rowKey="id"
              pagination={{ pageSize: 10, showSizeChanger: false }}
              size="small"
              scroll={{ x: "max-content" }}
              style={{ borderRadius: "8px", overflow: "hidden" }}
            />
          </Card>
        </>
      )}
    </div>
  );
}

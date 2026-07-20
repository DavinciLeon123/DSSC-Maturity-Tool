import React from "react";
import { createFileRoute, redirect, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { Card, Spin, Alert, Button, Typography, Tabs } from "antd";
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

// ---- Types ----------------------------------------------------------------

interface AdminHeatmapCell {
  yes: number;
  not_yet: number;
  n_a: number;
}

interface AdminHeatmapResponse {
  total_submitted: number;
  matrix: Record<string, Record<string, Record<string, AdminHeatmapCell>>>;
  topic_structure: Record<string, Array<{ topic_id: string; topic_label: string; codes: string[] }>>;
}

// ---- Labels ----------------------------------------------------------------

const CATEGORY_LABELS: Record<string, string> = {
  scheme: "Scheme",
  participants: "Participants",
  data: "Data",
  services: "Services",
};

const DIMENSION_LABELS = [
  { key: "human_readable", label: "Human readability" },
  { key: "machine_readable", label: "Machine readability" },
  { key: "trust_anchors", label: "Trust anchors" },
];

// ---- CountPill component ---------------------------------------------------

function CountPill({ count, color }: { count: number; color: "green" | "blue" | "grey" }) {
  const cfg = {
    green: { bg: "rgba(57,158,90,0.2)", color: "#399e5a" },
    blue:  { bg: "rgba(61,82,213,0.2)", color: "#3d52d5" },
    grey:  { bg: "rgba(204,204,204,0.8)", color: "#666" },
  }[color];
  return (
    <span
      style={{
        background: cfg.bg,
        color: cfg.color,
        borderRadius: "100px",
        padding: "4px 12px",
        fontSize: "0.85rem",
        fontFamily: "'Rubik', sans-serif",
        fontWeight: 600,
        minWidth: "36px",
        textAlign: "center",
        display: "inline-block",
      }}
    >
      {count}
    </span>
  );
}

// ---- HeatmapGrid component -------------------------------------------------

interface HeatmapGridProps {
  data: AdminHeatmapResponse | null;
  loading: boolean;
  error: string | null;
  typeLabel: string; // "DSI initiative" or "Service Provider initiative"
}

function HeatmapGrid({ data, loading, error, typeLabel }: HeatmapGridProps) {
  const categories = Object.keys(CATEGORY_LABELS);
  const gridCols = "200px repeat(3, 1fr)";

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", paddingTop: "4rem" }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return <Alert type="error" message={error} showIcon style={{ maxWidth: "600px" }} />;
  }

  if (!data) return null;

  return (
    <Card
      style={{
        borderRadius: "16px",
        boxShadow: "0 2px 12px rgba(6,0,79,0.08)",
        overflow: "hidden",
      }}
      styles={{ body: { padding: "1.5rem" } }}
    >
      <div style={{ overflowX: "auto" }}>
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
              {dim.label}
            </div>
          ))}
        </div>

        {/* Category group headers + topic rows */}
        <div style={{ display: "grid", gridTemplateColumns: gridCols }}>
          {categories.map((cat) => (
            <React.Fragment key={cat}>
              <div
                style={{
                  gridColumn: "1 / -1",
                  background: "#06004f",
                  padding: "10px 16px",
                  fontFamily: "'Rubik', sans-serif",
                  fontWeight: 600,
                  fontSize: "0.9rem",
                  color: "white",
                  borderBottom: "1px solid rgba(255,255,255,0.15)",
                }}
              >
                {CATEGORY_LABELS[cat]}
              </div>

              {(data.topic_structure[cat] ?? []).map((topic) => (
                <React.Fragment key={topic.topic_id}>
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

                  {DIMENSION_LABELS.map((dim) => {
                    const cell: AdminHeatmapCell =
                      data.matrix[cat]?.[dim.key]?.[topic.topic_id] ?? {
                        yes: 0,
                        not_yet: 0,
                        n_a: 0,
                      };
                    return (
                      <div
                        key={dim.key}
                        style={{
                          display: "flex",
                          justifyContent: "center",
                          alignItems: "center",
                          gap: "4px",
                          padding: "8px",
                          borderBottom: "1px solid #f0f0f0",
                        }}
                      >
                        <CountPill count={cell.yes} color="green" />
                        <CountPill count={cell.not_yet} color="blue" />
                        <CountPill count={cell.n_a} color="grey" />
                      </div>
                    );
                  })}
                </React.Fragment>
              ))}
            </React.Fragment>
          ))}
        </div>
      </div>

      <Text
        style={{
          fontFamily: "'Rubik', sans-serif",
          fontSize: "0.875rem",
          color: "rgba(6,0,79,0.6)",
          display: "block",
          marginTop: "1.5rem",
        }}
      >
        Based on{" "}
        <strong style={{ color: "#06004f" }}>{data.total_submitted}</strong>{" "}
        submitted {typeLabel}{data.total_submitted !== 1 ? "s" : ""}. Each cell shows:{" "}
        <CountPill count={0} color="green" /> Yes &nbsp;
        <CountPill count={0} color="blue" /> Not yet &nbsp;
        <CountPill count={0} color="grey" /> N/A
      </Text>
    </Card>
  );
}

// ---- AdminHeatmapPage component --------------------------------------------

export function AdminHeatmapPage() {
  // DSI state — fetched on mount
  const [dsiData, setDsiData] = useState<AdminHeatmapResponse | null>(null);
  const [dsiLoading, setDsiLoading] = useState(true);
  const [dsiError, setDsiError] = useState<string | null>(null);

  // SP state — fetched lazily on first tab activation
  const [spData, setSpData] = useState<AdminHeatmapResponse | null>(null);
  const [spLoading, setSpLoading] = useState(false);
  const [spError, setSpError] = useState<string | null>(null);
  const [spFetched, setSpFetched] = useState(false);

  // Fetch DSI on mount (dsiLoading already starts true — no need to set it again here)
  useEffect(() => {
    api
      .get<AdminHeatmapResponse>("/admin/heatmap?type=dsi")
      .then((res) => setDsiData(res.data))
      .catch(() => setDsiError("Failed to load DSI heatmap data."))
      .finally(() => setDsiLoading(false));
  }, []);

  // Lazy fetch SP on first tab activation
  function handleTabChange(key: string) {
    if (key === "sp" && !spFetched) {
      setSpFetched(true);
      setSpLoading(true);
      api
        .get<AdminHeatmapResponse>("/admin/heatmap?type=sp")
        .then((res) => setSpData(res.data))
        .catch(() => setSpError("Failed to load SP heatmap data."))
        .finally(() => setSpLoading(false));
    }
  }

  const tabItems = [
    {
      key: "dsi",
      label: "Aggregated Interoperability Heatmap for DSI's",
      children: (
        <HeatmapGrid
          data={dsiData}
          loading={dsiLoading}
          error={dsiError}
          typeLabel="DSI initiative"
        />
      ),
    },
    {
      key: "sp",
      label: "Aggregated Interoperability Heatmap for SP's",
      children: (
        <HeatmapGrid
          data={spData}
          loading={spLoading}
          error={spError}
          typeLabel="Service Provider initiative"
        />
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
          fontWeight: 700,
          color: "#06004f",
          marginBottom: "1.5rem",
          fontSize: "1.75rem",
        }}
      >
        Aggregated Interoperability Heatmap
      </Title>

      <Tabs
        defaultActiveKey="dsi"
        items={tabItems}
        onChange={handleTabChange}
      />
    </div>
  );
}

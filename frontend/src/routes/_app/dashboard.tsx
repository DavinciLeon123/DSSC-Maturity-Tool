import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Card, Button, Alert, Input, Select, Tag } from "antd";
import { api } from "../../lib/api";

export const Route = createFileRoute("/_app/dashboard")({
  component: DashboardPage,
});

interface UserMe {
  id: number;
  email: string;
  role: string;
}

interface FullInitiative {
  id: number;
  name: string;
  status: string;
  sector: string;
  sector_other?: string | null;
  contact_name?: string | null;
  contact_email?: string | null;
  organization?: string | null;
  description?: string | null;
}

const SECTOR_OPTIONS = [
  "Healthcare",
  "Finance",
  "Government",
  "Energy",
  "Education",
  "Transport",
  "Agriculture",
  "Other",
];

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: "0.875rem",
  fontWeight: 500,
  marginBottom: "0.375rem",
  color: "#06004f",
  fontFamily: "'Rubik', sans-serif",
};

function DashboardPage() {
  const navigate = useNavigate();
  const [user, setUser] = useState<UserMe | null>(null);
  const [initiative, setInitiative] = useState<FullInitiative | null>(null);
  const [hasNoInitiative, setHasNoInitiative] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [regForm, setRegForm] = useState({ name: "", sector: "", sector_other: "" });
  const [regLoading, setRegLoading] = useState(false);
  const [regError, setRegError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<UserMe>("/auth/me")
      .then((res) => setUser(res.data))
      .catch(() => setError("Could not load user info"));

    api
      .get<FullInitiative>("/initiatives/me")
      .then((res) => setInitiative(res.data))
      .catch((err) => {
        if (err.response?.status === 404) {
          setHasNoInitiative(true);
        }
      });
  }, []);

  async function handleRegisterInitiative(e: React.FormEvent) {
    e.preventDefault();
    if (!regForm.name.trim() || !regForm.sector) return;
    setRegLoading(true);
    setRegError(null);
    try {
      const body: Record<string, string | undefined> = {
        name: regForm.name.trim(),
        sector: regForm.sector,
      };
      if (regForm.sector === "Other" && regForm.sector_other.trim()) {
        body.sector_other = regForm.sector_other.trim();
      }
      const res = await api.post<FullInitiative>("/initiatives", body);
      setInitiative(res.data);
      setHasNoInitiative(false);
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } };
      setRegError(apiErr.response?.data?.detail ?? "Failed to register initiative. Please try again.");
    } finally {
      setRegLoading(false);
    }
  }

  async function handleGenerateReport() {
    if (!initiative) return;
    setReportLoading(true);
    setReportError(null);
    try {
      await api.post(`/initiatives/${initiative.id}/report/data`, {});
      navigate({ to: "/report" });
    } catch {
      setReportError("Failed to generate report. Make sure you have answered the questionnaire.");
    } finally {
      setReportLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: "900px", margin: "0 auto" }}>
      <h1
        style={{
          fontSize: "1.75rem",
          fontWeight: 700,
          color: "#06004f",
          marginBottom: "1.5rem",
          fontFamily: "'Rubik', sans-serif",
        }}
      >
        Dashboard
      </h1>

      {error && (
        <Alert type="error" message={error} style={{ marginBottom: "1rem" }} showIcon />
      )}

      {user ? (
        <Card
          style={{
            borderRadius: "16px",
            boxShadow: "0 2px 12px rgba(6,0,79,0.06)",
          }}
        >
          <p
            style={{
              fontSize: "1.1rem",
              color: "rgba(6,0,79,0.75)",
              fontFamily: "'Rubik', sans-serif",
            }}
          >
            Welcome, <strong style={{ color: "#06004f" }}>{user.email}</strong>
          </p>

          {/* Inline registration form — shown when user has no initiative */}
          {hasNoInitiative && !initiative ? (
            <Card
              style={{
                marginTop: "1.5rem",
                borderRadius: "16px",
                boxShadow: "0 2px 12px rgba(6,0,79,0.06)",
              }}
            >
              <h2
                style={{
                  fontSize: "1.1rem",
                  fontWeight: 700,
                  color: "#06004f",
                  marginBottom: "0.5rem",
                  fontFamily: "'Rubik', sans-serif",
                }}
              >
                Register Your Initiative
              </h2>
              <p
                style={{
                  fontSize: "0.875rem",
                  color: "rgba(6,0,79,0.6)",
                  marginBottom: "1.5rem",
                  fontFamily: "'Rubik', sans-serif",
                }}
              >
                Get started by registering your DSI initiative.
              </p>

              {regError && (
                <Alert
                  type="error"
                  message={regError}
                  style={{ marginBottom: "1rem" }}
                  showIcon
                />
              )}

              <form
                onSubmit={handleRegisterInitiative}
                style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
              >
                <div>
                  <label style={labelStyle}>Initiative Name</label>
                  <Input
                    value={regForm.name}
                    onChange={(e) => setRegForm((prev) => ({ ...prev, name: e.target.value }))}
                    required
                    size="large"
                    placeholder="Enter initiative name"
                    style={{ borderRadius: "8px", fontFamily: "'Rubik', sans-serif" }}
                  />
                </div>

                <div>
                  <label style={labelStyle}>Sector</label>
                  <Select
                    value={regForm.sector || undefined}
                    onChange={(value) => setRegForm((prev) => ({ ...prev, sector: value }))}
                    placeholder="Select a sector..."
                    size="large"
                    style={{ width: "100%", fontFamily: "'Rubik', sans-serif" }}
                    options={SECTOR_OPTIONS.map((s) => ({ label: s, value: s }))}
                  />
                </div>

                {regForm.sector === "Other" && (
                  <div>
                    <label style={labelStyle}>Specify Sector</label>
                    <Input
                      value={regForm.sector_other}
                      onChange={(e) => setRegForm((prev) => ({ ...prev, sector_other: e.target.value }))}
                      size="large"
                      placeholder="Describe your sector"
                      style={{ borderRadius: "8px", fontFamily: "'Rubik', sans-serif" }}
                    />
                  </div>
                )}

                <Button
                  type="primary"
                  htmlType="submit"
                  loading={regLoading}
                  size="large"
                  style={{
                    borderRadius: "8px",
                    fontFamily: "'Rubik', sans-serif",
                    fontWeight: 600,
                  }}
                >
                  Register Initiative
                </Button>
              </form>
            </Card>
          ) : null}

          {/* Initiative details + CTA — shown when initiative exists */}
          {initiative ? (
            <div style={{ marginTop: "1.5rem" }}>
              <Card
                style={{
                  borderRadius: "16px",
                  boxShadow: "0 2px 12px rgba(6,0,79,0.06)",
                  marginBottom: "1rem",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    flexWrap: "wrap",
                    gap: "1rem",
                  }}
                >
                  <div>
                    <h2
                      style={{
                        fontSize: "1.25rem",
                        fontWeight: 700,
                        color: "#06004f",
                        fontFamily: "'Rubik', sans-serif",
                        margin: 0,
                      }}
                    >
                      {initiative.name}
                    </h2>
                    <div style={{ marginTop: "0.5rem" }}>
                      <Tag
                        color={initiative.status === "submitted" ? "success" : "warning"}
                        style={{
                          fontFamily: "'Rubik', sans-serif",
                          fontWeight: 600,
                          textTransform: "uppercase",
                        }}
                      >
                        {{ draft: "Registered", active: "Active", submitted: "Submitted" }[initiative.status] ?? initiative.status}
                      </Tag>
                    </div>
                    <p
                      style={{
                        marginTop: "0.75rem",
                        fontSize: "0.875rem",
                        color: "rgba(6,0,79,0.75)",
                        fontFamily: "'Rubik', sans-serif",
                        margin: "0.75rem 0 0",
                      }}
                    >
                      Sector:{" "}
                      <strong style={{ color: "#06004f" }}>
                        {initiative.sector_other
                          ? `${initiative.sector} — ${initiative.sector_other}`
                          : initiative.sector}
                      </strong>
                    </p>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                    <Button
                      type="primary"
                      size="large"
                      onClick={() => navigate({ to: "/questionnaire" })}
                      style={{
                        borderRadius: "8px",
                        fontFamily: "'Rubik', sans-serif",
                        fontWeight: 600,
                      }}
                    >
                      {initiative.status === "submitted" ? "Retake Questionnaire" : "Start Questionnaire"}
                    </Button>

                    <Button
                      size="large"
                      onClick={handleGenerateReport}
                      loading={reportLoading}
                      style={{
                        borderRadius: "8px",
                        fontFamily: "'Rubik', sans-serif",
                        fontWeight: 600,
                      }}
                    >
                      Generate Heatmap
                    </Button>
                  </div>
                </div>
              </Card>

              {reportError && (
                <Alert
                  type="error"
                  message={reportError}
                  style={{ marginBottom: "1rem" }}
                  showIcon
                />
              )}
            </div>
          ) : null}

          {/* Loading state — initiative fetch still in progress */}
          {!hasNoInitiative && !initiative && !error ? (
            <p
              style={{
                marginTop: "1rem",
                fontSize: "0.875rem",
                color: "rgba(6,0,79,0.5)",
                fontFamily: "'Rubik', sans-serif",
              }}
            >
              Loading initiative...
            </p>
          ) : null}
        </Card>
      ) : !error ? (
        <p style={{ color: "rgba(6,0,79,0.6)", fontFamily: "'Rubik', sans-serif" }}>Loading...</p>
      ) : null}
    </div>
  );
}

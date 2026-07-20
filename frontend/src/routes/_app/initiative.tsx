import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Card, Button, Alert, Input, Select, Tag } from "antd";
import { api } from "../../lib/api";

export const Route = createFileRoute("/_app/initiative")({
  component: InitiativePage,
});

interface Initiative {
  id: number;
  name: string;
  description: string;
  sector: string;
  sector_other: string | null;
  contact_name: string;
  contact_email: string;
  organization: string;
  status: string;
  created_at: string;
  updated_at: string;
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

function InitiativePage() {
  const [initiative, setInitiative] = useState<Initiative | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [form, setForm] = useState({
    name: "",
    description: "",
    sector: "",
    sector_other: "",
    contact_name: "",
    contact_email: "",
    organization: "",
  });

  const [editForm, setEditForm] = useState({
    name: "",
    description: "",
    sector: "",
    sector_other: "",
    contact_name: "",
    contact_email: "",
    organization: "",
  });

  useEffect(() => {
    api
      .get<Initiative>("/initiatives/me")
      .then((res) => {
        setInitiative(res.data);
        setLoading(false);
      })
      .catch((err) => {
        if (err.response?.status === 404) {
          setNotFound(true);
          setShowForm(true);
        }
        setLoading(false);
      });
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    try {
      const body: Record<string, string | undefined> = {
        name: form.name,
        description: form.description,
        sector: form.sector,
        contact_name: form.contact_name,
        contact_email: form.contact_email,
        organization: form.organization,
      };
      if (form.sector === "Other" && form.sector_other) {
        body.sector_other = form.sector_other;
      }
      const res = await api.post<Initiative>("/initiatives", body);
      setInitiative(res.data);
      setNotFound(false);
      setShowForm(false);
      setSuccess("Initiative registered successfully!");
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } };
      setError(apiErr.response?.data?.detail ?? "Failed to create initiative");
    }
  };

  const handleEditChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setEditForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const startEdit = () => {
    if (initiative) {
      setEditForm({
        name: initiative.name,
        description: initiative.description,
        sector: initiative.sector,
        sector_other: initiative.sector_other ?? "",
        contact_name: initiative.contact_name,
        contact_email: initiative.contact_email,
        organization: initiative.organization,
      });
      setShowForm(true);
      setError(null);
    }
  };

  const handleEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (!initiative) return;
    try {
      const body: Record<string, string | undefined> = {
        name: editForm.name,
        description: editForm.description,
        sector: editForm.sector,
        contact_name: editForm.contact_name,
        contact_email: editForm.contact_email,
        organization: editForm.organization,
      };
      if (editForm.sector === "Other" && editForm.sector_other) {
        body.sector_other = editForm.sector_other;
      }
      const res = await api.patch<Initiative>(`/initiatives/${initiative.id}`, body);
      setInitiative(res.data);
      setShowForm(false);
      setSuccess("Initiative updated successfully!");
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } };
      setError(apiErr.response?.data?.detail ?? "Failed to update initiative");
    }
  };

  if (loading) {
    return <p style={{ color: "rgba(6,0,79,0.6)", fontFamily: "'Rubik', sans-serif" }}>Loading...</p>;
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
        My Initiative
      </h1>

      {success && (
        <Alert
          type="success"
          message={success}
          style={{ marginBottom: "1rem" }}
          showIcon
        />
      )}

      {initiative && !showForm ? (
        <Card
          style={{
            borderRadius: "16px",
            boxShadow: "0 2px 12px rgba(6,0,79,0.06)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              marginBottom: "1.5rem",
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
                  style={{ fontFamily: "'Rubik', sans-serif", fontWeight: 600, textTransform: "uppercase" }}
                >
                  {{ draft: "Registered", active: "Active", submitted: "Submitted" }[initiative.status] ?? initiative.status}
                </Tag>
              </div>
            </div>
            {initiative.status !== "submitted" && (
              <Button
                type="primary"
                onClick={startEdit}
                style={{
                  borderRadius: "8px",
                  fontFamily: "'Rubik', sans-serif",
                  fontWeight: 600,
                }}
              >
                Edit
              </Button>
            )}
          </div>
          <dl style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "0.75rem 1rem" }}>
            {[
              ["Organization", initiative.organization],
              ["Sector", initiative.sector_other ? `${initiative.sector} — ${initiative.sector_other}` : initiative.sector],
              ["Contact", `${initiative.contact_name} (${initiative.contact_email})`],
              ["Description", initiative.description],
            ].map(([label, value]) => (
              <>
                <dt key={`dt-${label}`} style={{ fontWeight: 600, color: "#06004f", fontSize: "0.875rem", fontFamily: "'Rubik', sans-serif" }}>{label}</dt>
                <dd key={`dd-${label}`} style={{ color: "rgba(6,0,79,0.75)", fontSize: "0.875rem", fontFamily: "'Rubik', sans-serif" }}>{value}</dd>
              </>
            ))}
          </dl>
        </Card>
      ) : null}

      {(notFound || showForm) && !initiative ? (
        <Card
          style={{
            borderRadius: "16px",
            boxShadow: "0 2px 12px rgba(6,0,79,0.06)",
          }}
        >
          <h2
            style={{
              fontSize: "1.1rem",
              fontWeight: 700,
              color: "#06004f",
              marginBottom: "1.5rem",
              fontFamily: "'Rubik', sans-serif",
            }}
          >
            Register Your DSI Initiative
          </h2>
          {error && (
            <Alert
              type="error"
              message={error}
              style={{ marginBottom: "1rem" }}
              showIcon
            />
          )}
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {[
              { name: "name", label: "Initiative Name" },
              { name: "organization", label: "Organization" },
              { name: "contact_name", label: "Contact Person Name" },
              { name: "contact_email", label: "Contact Email" },
            ].map(({ name, label }) => (
              <div key={name}>
                <label style={labelStyle}>{label}</label>
                <Input
                  name={name}
                  value={form[name as keyof typeof form]}
                  onChange={handleChange}
                  required
                  size="large"
                  style={{ borderRadius: "8px", fontFamily: "'Rubik', sans-serif" }}
                />
              </div>
            ))}
            <div>
              <label style={labelStyle}>Sector</label>
              <Select
                value={form.sector || undefined}
                onChange={(value) => setForm((prev) => ({ ...prev, sector: value }))}
                placeholder="Select a sector..."
                size="large"
                style={{ width: "100%", fontFamily: "'Rubik', sans-serif" }}
                options={SECTOR_OPTIONS.map((s) => ({ label: s, value: s }))}
              />
            </div>
            {form.sector === "Other" && (
              <div>
                <label style={labelStyle}>Specify Sector</label>
                <Input
                  name="sector_other"
                  value={form.sector_other}
                  onChange={handleChange}
                  required
                  size="large"
                  style={{ borderRadius: "8px", fontFamily: "'Rubik', sans-serif" }}
                />
              </div>
            )}
            <div>
              <label style={labelStyle}>
                Description{" "}
                <span style={{ fontWeight: 400, color: "rgba(6,0,79,0.5)" }}>(optional)</span>
              </label>
              <Input.TextArea
                name="description"
                value={form.description}
                onChange={handleChange}
                rows={4}
                style={{ borderRadius: "8px", fontFamily: "'Rubik', sans-serif" }}
              />
            </div>
            <Button
              type="primary"
              htmlType="submit"
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

      {initiative && showForm && (
        <div style={{ marginTop: "1rem" }}>
          <Button
            onClick={() => { setShowForm(false); setError(null); }}
            style={{
              marginBottom: "1rem",
              borderRadius: "8px",
              fontFamily: "'Rubik', sans-serif",
            }}
          >
            Cancel
          </Button>
          <Card
            style={{
              borderRadius: "16px",
              boxShadow: "0 2px 12px rgba(6,0,79,0.06)",
            }}
          >
            <h2
              style={{
                fontSize: "1.1rem",
                fontWeight: 700,
                color: "#06004f",
                marginBottom: "1.5rem",
                fontFamily: "'Rubik', sans-serif",
              }}
            >
              Edit Initiative
            </h2>
            {error && (
              <Alert
                type="error"
                message={error}
                style={{ marginBottom: "1rem" }}
                showIcon
              />
            )}
            <form onSubmit={handleEdit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              {[
                { name: "name", label: "Initiative Name" },
                { name: "organization", label: "Organization" },
                { name: "contact_name", label: "Contact Person Name" },
                { name: "contact_email", label: "Contact Email" },
              ].map(({ name, label }) => (
                <div key={name}>
                  <label style={labelStyle}>{label}</label>
                  <Input
                    name={name}
                    value={editForm[name as keyof typeof editForm]}
                    onChange={handleEditChange}
                    required
                    size="large"
                    style={{ borderRadius: "8px", fontFamily: "'Rubik', sans-serif" }}
                  />
                </div>
              ))}
              <div>
                <label style={labelStyle}>Sector</label>
                <Select
                  value={editForm.sector || undefined}
                  onChange={(value) => setEditForm((prev) => ({ ...prev, sector: value }))}
                  placeholder="Select a sector..."
                  size="large"
                  style={{ width: "100%", fontFamily: "'Rubik', sans-serif" }}
                  options={SECTOR_OPTIONS.map((s) => ({ label: s, value: s }))}
                />
              </div>
              {editForm.sector === "Other" && (
                <div>
                  <label style={labelStyle}>Specify Sector</label>
                  <Input
                    name="sector_other"
                    value={editForm.sector_other}
                    onChange={handleEditChange}
                    required
                    size="large"
                    style={{ borderRadius: "8px", fontFamily: "'Rubik', sans-serif" }}
                  />
                </div>
              )}
              <div>
                <label style={labelStyle}>
                  Description{" "}
                  <span style={{ fontWeight: 400, color: "rgba(6,0,79,0.5)" }}>(optional)</span>
                </label>
                <Input.TextArea
                  name="description"
                  value={editForm.description}
                  onChange={handleEditChange}
                  rows={4}
                  style={{ borderRadius: "8px", fontFamily: "'Rubik', sans-serif" }}
                />
              </div>
              <Button
                type="primary"
                htmlType="submit"
                size="large"
                style={{
                  borderRadius: "8px",
                  fontFamily: "'Rubik', sans-serif",
                  fontWeight: 600,
                }}
              >
                Save Changes
              </Button>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
}

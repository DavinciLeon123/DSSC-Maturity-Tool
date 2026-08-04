import { createFileRoute, Link, useNavigate, useSearch } from "@tanstack/react-router";
import { useState } from "react";
import { Input, Button, Alert } from "antd";
import logoSrc from "../../assets/logo-dssc-color.png";

export const Route = createFileRoute("/_auth/reset-password")({
  component: ResetPasswordPage,
});

function ResetPasswordPage() {
  const navigate = useNavigate();
  const search = useSearch({ from: "/_auth/reset-password" });
  const token = (search as Record<string, string>).token ?? "";

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!token) {
    return (
      <div style={{ minHeight: "100vh", background: "#008ecf", display: "flex", alignItems: "center", justifyContent: "center", padding: "2rem" }}>
        <div style={{ background: "white", borderRadius: "16px", padding: "2.5rem", width: "100%", maxWidth: "420px", boxShadow: "0 8px 40px rgba(0,142,207,0.15)", textAlign: "center" }}>
          <Alert message="Invalid or missing reset token." type="error" style={{ marginBottom: "1rem" }} showIcon />
          <Link to="/forgot-password" style={{ color: "#76b82a", fontWeight: 600, textDecoration: "none", fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif" }}>
            Request a new reset link
          </Link>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (newPassword.length < 12) {
      setError("Password must be at least 12 characters.");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(
        (import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1") + "/auth/reset-password",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token, new_password: newPassword }),
        }
      );
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail ?? "Reset failed. The link may have expired.");
        return;
      }
      navigate({ to: "/login", search: { reset: "success" } });
    } catch {
      setError("Network error — is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "#008ecf", display: "flex", alignItems: "center", justifyContent: "center", padding: "2rem" }}>
      <div style={{ background: "white", borderRadius: "16px", padding: "2.5rem", width: "100%", maxWidth: "420px", boxShadow: "0 8px 40px rgba(0,142,207,0.15)" }}>
        <div style={{ marginBottom: "2rem", textAlign: "center" }}>
          <img src={logoSrc} alt="DSSC logo" style={{ width: "76px", height: "auto", display: "block", margin: "0 auto 0.75rem" }} />
          <div style={{ fontSize: "0.75rem", color: "#76b82a", fontWeight: 600, letterSpacing: "0.1em", marginBottom: "0.5rem", fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif" }}>DSSC</div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#008ecf", fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif", margin: 0 }}>Set New Password</h1>
        </div>
        {error && (
          <Alert message={error} type="error" style={{ marginBottom: 16 }} showIcon />
        )}
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "1rem" }}>
            <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.375rem", color: "#008ecf", fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif" }}>New Password</label>
            <Input.Password
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              minLength={12}
              placeholder="Minimum 12 characters"
              size="large"
            />
          </div>
          <div style={{ marginBottom: "1.5rem" }}>
            <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.375rem", color: "#008ecf", fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif" }}>Confirm Password</label>
            <Input.Password
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              size="large"
            />
          </div>
          <Button
            type="primary"
            htmlType="submit"
            block
            size="large"
            loading={loading}
            style={{ borderRadius: "8px", height: "48px", fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif", fontWeight: 600 }}
          >
            Reset Password
          </Button>
        </form>
      </div>
    </div>
  );
}

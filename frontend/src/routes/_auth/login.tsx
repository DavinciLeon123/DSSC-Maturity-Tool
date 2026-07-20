import { createFileRoute, useNavigate, Link, useSearch } from "@tanstack/react-router";
import { useState } from "react";
import { Input, Button, Alert } from "antd";
import { authStore } from "../../lib/auth";
import logoSrc from "../../assets/logo-coe-dsc.svg";

export const Route = createFileRoute("/_auth/login")({
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const search = useSearch({ from: "/_auth/login" });
  const sessionExpired = (search as Record<string, string>).session === "expired";
  const resetSuccess = (search as Record<string, string>).reset === "success";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append("username", email);
      params.append("password", password);
      const res = await fetch(
        (import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1") + "/auth/login",
        { method: "POST", body: params, headers: { "Content-Type": "application/x-www-form-urlencoded" } }
      );
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail ?? `Login failed (${res.status})`);
        return;
      }
      const data = await res.json();
      authStore.setToken(data.access_token);
      navigate({ to: "/dashboard" });
    } catch {
      setError("Network error — is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "#06004f", display: "flex", alignItems: "center", justifyContent: "center", padding: "2rem" }}>
      <div style={{ background: "white", borderRadius: "16px", padding: "2.5rem", width: "100%", maxWidth: "420px", boxShadow: "0 8px 40px rgba(6,0,79,0.15)" }}>
        {sessionExpired && (
          <Alert message="Your session expired. Please log in again." type="warning" style={{ marginBottom: 16 }} showIcon />
        )}
        {resetSuccess && (
          <Alert message="Password reset successfully. Please log in with your new password." type="success" style={{ marginBottom: 16 }} showIcon />
        )}
        <div style={{ marginBottom: "2rem", textAlign: "center" }}>
          <img src={logoSrc} alt="CoE DSC logo" style={{ width: "76px", height: "auto", display: "block", margin: "0 auto 0.75rem" }} />
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#06004f", fontFamily: "'Rubik', sans-serif", margin: 0 }}>Sign In</h1>
        </div>
        {error && (
          <Alert message={error} type="error" style={{ marginBottom: 16 }} showIcon />
        )}
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "1rem" }}>
            <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.375rem", color: "#06004f", fontFamily: "'Rubik', sans-serif" }}>
              Email
            </label>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              size="large"
            />
          </div>
          <div style={{ marginBottom: "1.5rem" }}>
            <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.375rem", color: "#06004f", fontFamily: "'Rubik', sans-serif" }}>
              Password
            </label>
            <Input.Password
              value={password}
              onChange={(e) => setPassword(e.target.value)}
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
            style={{ borderRadius: "8px", height: "48px", fontFamily: "'Rubik', sans-serif", fontWeight: 600 }}
          >
            Sign In
          </Button>
        </form>
        <p style={{ textAlign: "center", marginTop: "1.5rem", fontSize: "0.875rem", color: "#6B7280" }}>
          No account?{" "}
          <Link to="/register" style={{ color: "#399e5a", fontWeight: 600, textDecoration: "none" }}>Register</Link>
        </p>
        <p style={{ textAlign: "center", marginTop: "0.75rem", fontSize: "0.875rem", color: "#6B7280" }}>
          <Link to="/forgot-password" style={{ color: "#399e5a", fontWeight: 600, textDecoration: "none" }}>
            Forgot your password?
          </Link>
        </p>
      </div>
    </div>
  );
}

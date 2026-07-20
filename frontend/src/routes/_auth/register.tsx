import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Input, Button, Alert } from "antd";
import logoSrc from "../../assets/logo-coe-dsc.svg";

export const Route = createFileRoute("/_auth/register")({
  component: RegisterPage,
});

function RegisterPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [participantType, setParticipantType] = useState<"DSI" | "SP">("DSI");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(
        (import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1") + "/auth/register",
        {
          method: "POST",
          body: JSON.stringify({ email, password, participant_type: participantType }),
          headers: { "Content-Type": "application/json" },
        }
      );
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail ?? `Registration failed (${res.status})`);
        return;
      }
      navigate({ to: "/login" });
    } catch {
      setError("Network error — is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "#06004f", display: "flex", alignItems: "center", justifyContent: "center", padding: "2rem" }}>
      <div style={{ background: "white", borderRadius: "16px", padding: "2.5rem", width: "100%", maxWidth: "420px", boxShadow: "0 8px 40px rgba(6,0,79,0.15)" }}>
        <div style={{ marginBottom: "2rem", textAlign: "center" }}>
          <img src={logoSrc} alt="CoE DSC logo" style={{ width: "76px", height: "auto", display: "block", margin: "0 auto 0.75rem" }} />
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#06004f", fontFamily: "'Rubik', sans-serif", margin: 0 }}>Create Account</h1>
        </div>
        {error && (
          <Alert message={error} type="error" style={{ marginBottom: 16 }} showIcon />
        )}
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "1rem" }}>
            <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.375rem", color: "#06004f", fontFamily: "'Rubik', sans-serif" }}>Email</label>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              size="large"
            />
          </div>
          <div style={{ marginBottom: "0.5rem" }}>
            <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.375rem", color: "#06004f", fontFamily: "'Rubik', sans-serif" }}>Password</label>
            <Input.Password
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={12}
              size="large"
            />
          </div>
          <p style={{ fontSize: "0.75rem", color: "rgba(6,0,79,0.5)", marginBottom: "1.5rem", fontFamily: "'Rubik', sans-serif" }}>
            Minimum 12 characters required.
          </p>
          <div style={{ marginBottom: "1.5rem" }}>
            <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.75rem", color: "#06004f", fontFamily: "'Rubik', sans-serif" }}>
              I am a:
            </label>
            <div style={{ display: "flex", gap: "0.75rem" }}>
              {(["DSI", "SP"] as const).map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setParticipantType(type)}
                  style={{
                    flex: 1,
                    padding: "0.75rem",
                    border: `2px solid ${participantType === type ? "#399e5a" : "rgba(6,0,79,0.2)"}`,
                    background: participantType === type ? "#399e5a" : "white",
                    color: participantType === type ? "white" : "#06004f",
                    borderRadius: "8px",
                    fontWeight: 600,
                    cursor: "pointer",
                    fontSize: "0.875rem",
                    fontFamily: "'Rubik', sans-serif",
                    transition: "all 0.15s",
                  }}
                >
                  {type === "DSI" ? "DSI" : "SP"}
                </button>
              ))}
            </div>
            <p style={{ fontSize: "0.75rem", color: "rgba(6,0,79,0.5)", marginTop: "0.5rem", fontFamily: "'Rubik', sans-serif" }}>
              {participantType === "DSI" ? "Data Space Initiative" : "Service Provider"}
            </p>
          </div>
          <Button
            type="primary"
            htmlType="submit"
            block
            size="large"
            loading={loading}
            style={{ borderRadius: "8px", height: "48px", fontFamily: "'Rubik', sans-serif", fontWeight: 600 }}
          >
            Register
          </Button>
        </form>
        <p style={{ textAlign: "center", marginTop: "1.5rem", fontSize: "0.875rem", color: "rgba(6,0,79,0.5)", fontFamily: "'Rubik', sans-serif" }}>
          Already have an account?{" "}
          <Link to="/login" style={{ color: "#399e5a", fontWeight: 600, textDecoration: "none" }}>Sign In</Link>
        </p>
      </div>
    </div>
  );
}

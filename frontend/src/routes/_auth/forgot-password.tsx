import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Input, Button, Alert } from "antd";
import logoSrc from "../../assets/logo-dssc-color.png";

export const Route = createFileRoute("/_auth/forgot-password")({
  component: ForgotPasswordPage,
});

function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(
        (import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1") + "/auth/forgot-password",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email }),
        }
      );
      if (!res.ok) {
        setError("Something went wrong. Please try again.");
        return;
      }
      setSent(true);
    } catch {
      setError("Network error — is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "#008ecf", display: "flex", alignItems: "center", justifyContent: "center", padding: "2rem" }}>
      <div style={{ background: "white", borderRadius: "0", padding: "2.5rem", width: "100%", maxWidth: "420px", boxShadow: "0 8px 40px rgba(0,142,207,0.15)" }}>
        <div style={{ marginBottom: "2rem", textAlign: "center" }}>
          <img src={logoSrc} alt="DSSC logo" style={{ width: "76px", height: "auto", display: "block", margin: "0 auto 0.75rem" }} />
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#008ecf", fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif", margin: 0 }}>Reset Password</h1>
        </div>

        {sent ? (
          <div>
            <Alert
              message={`If ${email} is registered, a reset link has been sent. Check your inbox (and spam folder).`}
              type="success"
              style={{ marginBottom: "1.5rem" }}
              showIcon
            />
            <p style={{ textAlign: "center", fontSize: "0.875rem", fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif" }}>
              <Link to="/login" style={{ color: "#76b82a", fontWeight: 600, textDecoration: "none" }}>
                Back to Sign In
              </Link>
            </p>
          </div>
        ) : (
          <>
            <p style={{ fontSize: "0.875rem", color: "rgba(0,142,207,0.6)", marginBottom: "1.5rem", fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif" }}>
              Enter your email address and we'll send you a link to reset your password.
            </p>
            {error && (
              <Alert message={error} type="error" style={{ marginBottom: 16 }} showIcon />
            )}
            <form onSubmit={handleSubmit}>
              <div style={{ marginBottom: "1.5rem" }}>
                <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.375rem", color: "#008ecf", fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif" }}>Email</label>
                <Input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
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
                style={{ borderRadius: "0", height: "48px", fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif", fontWeight: 600 }}
              >
                Send Reset Link
              </Button>
            </form>
            <p style={{ textAlign: "center", marginTop: "1.5rem", fontSize: "0.875rem", fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif" }}>
              <Link to="/login" style={{ color: "#76b82a", fontWeight: 600, textDecoration: "none" }}>
                Back to Sign In
              </Link>
            </p>
          </>
        )}
      </div>
    </div>
  );
}

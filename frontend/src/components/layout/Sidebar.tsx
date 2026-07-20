import { Link, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { authStore } from "../../lib/auth";
import { api } from "../../lib/api";

export function Sidebar() {
  const navigate = useNavigate();

  const { data: currentUser } = useQuery<{ role: string; email: string }>({
    queryKey: ["current-user-role"],
    queryFn: async () => {
      const res = await api.get<{ role: string; email: string }>("/auth/me");
      return res.data;
    },
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes — role doesn't change during a session
  });

  const isAdmin = currentUser?.role === "ADMIN";

  const handleLogout = () => {
    authStore.clearToken();
    navigate({ to: "/" });
  };

  const navItems: Array<{
    label: string;
    to:
      | "/dashboard"
      | "/initiative"
      | "/questionnaire"
      | "/about"
      | "/admin";
  }> = [
    { label: "Dashboard", to: "/dashboard" },
    { label: "My Initiative", to: "/initiative" },
    { label: "Questionnaire", to: "/questionnaire" },
    { label: "About", to: "/about" },
    ...(isAdmin ? [{ label: "Admin", to: "/admin" as const }] : []),
  ];

  return (
    <nav
      style={{
        width: "240px",
        minHeight: "100vh",
        background: "var(--color-navy)",
        color: "white",
        display: "flex",
        flexDirection: "column",
        padding: "1.5rem 0",
      }}
    >
      <div style={{ padding: "0 1.5rem", marginBottom: "2rem" }}>
        <div
          style={{
            fontSize: "0.75rem",
            color: "var(--color-green)",
            fontWeight: 600,
            letterSpacing: "0.1em",
            marginBottom: "0.25rem",
          }}
        >
          CoE-DSC
        </div>
        <div style={{ fontWeight: 700, fontSize: "1rem" }}>MAMI Checker</div>
      </div>
      <div style={{ flex: 1 }}>
        {navItems.map(({ label, to }) => (
          <Link
            key={to}
            to={to}
            style={{
              display: "block",
              padding: "0.75rem 1.5rem",
              color: "rgba(255,255,255,0.8)",
              textDecoration: "none",
              fontWeight: 500,
            }}
            activeProps={{
              style: {
                color: "var(--color-green)",
                background: "rgba(255,255,255,0.08)",
              },
            }}
          >
            {label}
          </Link>
        ))}
      </div>
      <button
        onClick={handleLogout}
        style={{
          margin: "1rem 1.5rem 0",
          padding: "0.75rem",
          background: "transparent",
          color: "rgba(255,255,255,0.6)",
          border: "1px solid rgba(255,255,255,0.2)",
          borderRadius: "var(--border-radius-sm)",
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        Log Out
      </button>
    </nav>
  );
}

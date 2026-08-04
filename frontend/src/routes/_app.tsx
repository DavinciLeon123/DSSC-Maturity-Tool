import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";
import { authStore } from "../lib/auth";
import { TopNav } from "../components/layout/TopNav";

export const Route = createFileRoute("/_app")({
  beforeLoad: () => {
    if (!authStore.isAuthenticated()) {
      throw redirect({ to: "/login" });
    }
  },
  component: AppLayout,
});

function AppLayout() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', background: 'linear-gradient(135deg, rgba(118,184,42,0.06) 0%, rgba(0,142,207,0.10) 60%, rgba(255,255,255,0) 100%), #fff' }}>
      <TopNav />
      <main style={{ flex: 1, padding: '2rem' }}>
        <Outlet />
      </main>
    </div>
  );
}

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
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', background: 'linear-gradient(90deg, rgba(57,158,90,0.1) 0%, rgba(57,158,90,0.1) 100%), white' }}>
      <TopNav />
      <main style={{ flex: 1, padding: '2rem' }}>
        <Outlet />
      </main>
    </div>
  );
}

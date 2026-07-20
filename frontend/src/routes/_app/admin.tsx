import { createFileRoute, redirect, Outlet } from "@tanstack/react-router";
import { api } from "../../lib/api";

export const Route = createFileRoute("/_app/admin")({
  beforeLoad: async () => {
    try {
      const res = await api.get<{ role: string }>("/auth/me");
      if (res.data.role !== "ADMIN") {
        throw redirect({ to: "/dashboard" });
      }
    } catch (err: unknown) {
      if (err && typeof err === "object" && "to" in err) throw err;
      throw redirect({ to: "/dashboard" });
    }
  },
  component: () => <Outlet />,
});

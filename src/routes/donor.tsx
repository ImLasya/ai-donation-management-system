import { createFileRoute, Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { useApp } from "@/context/AppContext";
import { useEffect } from "react";

export const Route = createFileRoute("/donor")({
  component: DonorLayout,
});

function DonorLayout() {
  const { user } = useApp();
  const navigate = useNavigate();
  const location = useRouterState({ select: (s) => s.location });

  useEffect(() => {
    if (!user) {
      navigate({
        to: "/login",
        search: { redirect: location.pathname + location.search },
      });
      return;
    }
    if (user.role !== "donor") {
      const dest = user.role === "ngo" ? "/ngo/dashboard" : "/admin/dashboard";
      navigate({ to: dest });
    }
  }, [user, navigate, location]);

  if (!user || user.role !== "donor") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return <Outlet />;
}

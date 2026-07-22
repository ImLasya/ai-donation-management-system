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
    
    const isTrackRoute = location.pathname.includes("/track/");
    if (user.role !== "donor" && (!isTrackRoute || user.role !== "ngo")) {
      const dest = user.role === "ngo" ? "/ngo/dashboard" : "/admin/dashboard";
      navigate({ to: dest });
    }
  }, [user, navigate, location]);

  const isTrackRoute = location.pathname.includes("/track/");
  if (!user || (user.role !== "donor" && (!isTrackRoute || user.role !== "ngo"))) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return <Outlet />;
}

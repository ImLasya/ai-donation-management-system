import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/ngo/demands")({
  component: () => <Outlet />,
});

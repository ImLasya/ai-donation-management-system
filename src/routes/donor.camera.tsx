import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/donor/camera")({
  beforeLoad: () => {
    throw redirect({ to: "/donor/donate", replace: true });
  },
  component: () => null,
});

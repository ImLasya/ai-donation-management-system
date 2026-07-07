import { createFileRoute } from "@tanstack/react-router";
import { NotificationsPage } from "./donor.notifications";
export const Route = createFileRoute("/ngo/notifications")({
  head: () => ({ meta: [{ title: "Notifications — Donate" }] }),
  component: () => <NotificationsPage role="ngo" />,
});

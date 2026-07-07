import { createFileRoute } from "@tanstack/react-router";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, EmptyState } from "@/components/shared/ui";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useApp } from "@/context/AppContext";
import { Bell, Check, Trash2, CheckCheck } from "lucide-react";

export const Route = createFileRoute("/donor/notifications")({
  head: () => ({ meta: [{ title: "Notifications — Donate" }] }),
  component: () => <NotificationsPage role="donor" />,
});

export function NotificationsPage({ role }: { role: "donor" | "ngo" }) {
  const { notifications, markRead, markAllRead, removeNotification } = useApp();
  return (
    <DashboardShell role={role}>
      <PageHeader
        title="Notifications"
        subtitle="Stay on top of matches, pickups, and updates."
        action={
          <Button variant="outline" className="gap-2" onClick={markAllRead}>
            <CheckCheck className="h-4 w-4" /> Mark all read
          </Button>
        }
      />
      {notifications.length === 0 ? (
        <EmptyState icon={Bell} title="No notifications" message="You're all caught up." />
      ) : (
        <div className="space-y-3">
          {notifications.map((n) => (
            <Card
              key={n.id}
              className={`flex items-start justify-between gap-3 p-4 ${n.read ? "" : "border-l-4 border-l-primary"}`}
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-medium text-foreground">{n.title}</p>
                  <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                    {n.type}
                  </span>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">{n.message}</p>
                <p className="mt-1 text-xs text-muted-foreground">{n.timestamp}</p>
              </div>
              <div className="flex shrink-0 gap-1">
                {!n.read && (
                  <Button
                    size="icon"
                    variant="ghost"
                    aria-label="Mark read"
                    onClick={() => markRead(n.id)}
                  >
                    <Check className="h-4 w-4" />
                  </Button>
                )}
                <Button
                  size="icon"
                  variant="ghost"
                  aria-label="Delete"
                  onClick={() => removeNotification(n.id)}
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </DashboardShell>
  );
}

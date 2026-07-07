import { createFileRoute } from "@tanstack/react-router";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, StatusBadge } from "@/components/shared/ui";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { NGOS } from "@/data/mock";
import { HeartHandshake, ShieldCheck, Check, X, MapPin } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/admin/ngos")({
  head: () => ({ meta: [{ title: "Manage NGOs — Donate" }] }),
  component: ManageNGOs,
});

function ManageNGOs() {
  return (
    <DashboardShell role="admin">
      <PageHeader title="Manage NGOs" subtitle="Approve, verify, and moderate organisations." />
      <div className="grid gap-4">
        {NGOS.map((n) => (
          <Card
            key={n.id}
            className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="flex items-center gap-3">
              <div className="grid h-11 w-11 place-items-center rounded-xl bg-primary/10 text-primary">
                <HeartHandshake className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-1">
                  <p className="truncate font-semibold text-foreground">{n.name}</p>
                  {n.verified && <ShieldCheck className="h-4 w-4 text-primary" />}
                </div>
                <p className="flex items-center gap-1 text-xs text-muted-foreground">
                  <MapPin className="h-3 w-3" />
                  {n.city}, {n.state}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <StatusBadge status={n.verified ? "Active" : "Medium"} />
              {n.verified ? (
                <Button
                  size="sm"
                  variant="outline"
                  className="gap-1"
                  onClick={() => toast("NGO suspended")}
                >
                  <X className="h-4 w-4" /> Suspend
                </Button>
              ) : (
                <>
                  <Button
                    size="sm"
                    className="gap-1"
                    onClick={() => toast.success("NGO approved & verified")}
                  >
                    <Check className="h-4 w-4" /> Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="gap-1"
                    onClick={() => toast("NGO rejected")}
                  >
                    <X className="h-4 w-4" /> Reject
                  </Button>
                </>
              )}
            </div>
          </Card>
        ))}
      </div>
    </DashboardShell>
  );
}

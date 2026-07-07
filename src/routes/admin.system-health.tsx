import { createFileRoute } from "@tanstack/react-router";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, StatusBadge, StatCard, SectionCard } from "@/components/shared/ui";
import { Card } from "@/components/ui/card";
import { Server, Database, ScanSearch, Sparkles, Bell, HardDrive, Activity } from "lucide-react";

export const Route = createFileRoute("/admin/system-health")({
  head: () => ({ meta: [{ title: "System Health — Donate" }] }),
  component: Health,
});

const SERVICES = [
  { icon: Server, name: "API Gateway", status: "Operational" },
  { icon: Database, name: "Database", status: "Operational" },
  { icon: ScanSearch, name: "AI Detection Service", status: "Degraded" },
  { icon: Sparkles, name: "Matching Engine", status: "Operational" },
  { icon: Bell, name: "Notification Service", status: "Operational" },
  { icon: HardDrive, name: "Storage Service", status: "Operational" },
];
const EVENTS = [
  ["AI Detection latency elevated", "12 min ago"],
  ["Matching engine deployed v2.3", "2 h ago"],
  ["Database backup completed", "6 h ago"],
];

function Health() {
  return (
    <DashboardShell role="admin">
      <PageHeader title="System Health" subtitle="Live status of platform services." />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="API Response Time" value="118ms" icon={Activity} tone="success" />
        <StatCard label="Detection Requests" value="4,210" icon={ScanSearch} />
        <StatCard label="Match Requests" value="3,980" icon={Sparkles} tone="secondary" />
        <StatCard label="Error Rate" value="0.4%" icon={Activity} tone="accent" />
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="grid gap-4 sm:grid-cols-2 lg:col-span-2">
          {SERVICES.map((s) => (
            <Card key={s.name} className="flex items-center justify-between p-5">
              <div className="flex items-center gap-3">
                <div className="grid h-10 w-10 place-items-center rounded-lg bg-primary/10 text-primary">
                  <s.icon className="h-5 w-5" />
                </div>
                <p className="font-medium text-foreground">{s.name}</p>
              </div>
              <StatusBadge status={s.status} />
            </Card>
          ))}
        </div>
        <SectionCard title="Recent Events">
          <ol className="space-y-3">
            {EVENTS.map(([e, t]) => (
              <li key={e} className="border-l-2 border-border pl-3">
                <p className="text-sm text-foreground">{e}</p>
                <p className="text-xs text-muted-foreground">{t}</p>
              </li>
            ))}
          </ol>
        </SectionCard>
      </div>
    </DashboardShell>
  );
}

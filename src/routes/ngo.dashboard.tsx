import { createFileRoute, Link } from "@tanstack/react-router";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, StatCard, StatusBadge, SectionCard } from "@/components/shared/ui";
import { Button } from "@/components/ui/button";
import { useApp } from "@/context/AppContext";
import { DEMAND_SUPPLY, DONATIONS } from "@/data/mock";
import { ClipboardList, Flame, Truck, Users, PlusCircle, ArrowRight } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";

export const Route = createFileRoute("/ngo/dashboard")({
  head: () => ({ meta: [{ title: "NGO Dashboard — Donate" }] }),
  component: Dashboard,
});

function Dashboard() {
  const { demands } = useApp();
  const active = demands.filter(
    (d) => d.status === "Active" || d.status === "Partially Fulfilled",
  ).length;
  const high = demands.filter((d) => d.priority === "High" || d.priority === "Critical").length;
  return (
    <DashboardShell role="ngo">
      <PageHeader
        title="NGO Dashboard"
        subtitle="Manage demands and incoming donations."
        action={
          <Button asChild className="gap-2">
            <Link to="/ngo/demands/new">
              <PlusCircle className="h-4 w-4" /> New Demand
            </Link>
          </Button>
        }
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Active Demands" value={active} icon={ClipboardList} />
        <StatCard label="High Priority" value={high} icon={Flame} tone="accent" />
        <StatCard
          label="Incoming Donations"
          value={DONATIONS.length}
          icon={Truck}
          tone="secondary"
        />
        <StatCard label="Beneficiaries" value="4,200" icon={Users} tone="success" />
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <SectionCard title="Demand vs Supply" className="lg:col-span-2">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={DEMAND_SUPPLY}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
              <XAxis dataKey="month" tickLine={false} axisLine={false} fontSize={12} />
              <YAxis tickLine={false} axisLine={false} fontSize={12} />
              <Tooltip />
              <Legend />
              <Bar dataKey="demand" fill="var(--secondary)" radius={[6, 6, 0, 0]} />
              <Bar dataKey="supply" fill="var(--primary)" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </SectionCard>
        <SectionCard title="Urgent Needs">
          <div className="space-y-3">
            {demands
              .filter((d) => d.priority === "Critical" || d.priority === "High")
              .slice(0, 4)
              .map((d) => (
                <div
                  key={d.id}
                  className="flex items-center justify-between rounded-lg border border-border p-3"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-foreground">{d.itemName}</p>
                    <p className="text-xs text-muted-foreground">
                      {d.quantityFulfilled}/{d.quantityRequired}
                    </p>
                  </div>
                  <StatusBadge status={d.priority} />
                </div>
              ))}
          </div>
        </SectionCard>
      </div>
      <SectionCard
        title="Recent Matched Donations"
        className="mt-6"
        action={
          <Button asChild variant="ghost" size="sm" className="gap-1">
            <Link to="/ngo/incoming">
              View all <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        }
      >
        <div className="space-y-3">
          {DONATIONS.map((d) => (
            <div
              key={d.id}
              className="flex items-center justify-between rounded-lg border border-border p-3"
            >
              <div>
                <p className="text-sm font-medium text-foreground">{d.id}</p>
                <p className="text-xs text-muted-foreground">
                  {d.items.length} item types · {d.date}
                </p>
              </div>
              <StatusBadge status={d.status} />
            </div>
          ))}
        </div>
      </SectionCard>
    </DashboardShell>
  );
}

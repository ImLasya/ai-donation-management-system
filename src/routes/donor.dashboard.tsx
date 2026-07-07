import { createFileRoute, Link } from "@tanstack/react-router";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, StatCard, StatusBadge, SectionCard } from "@/components/shared/ui";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useApp } from "@/context/AppContext";
import { DONATIONS, CATEGORY_CHART, MONTHLY_CHART, NGOS } from "@/data/mock";
import { Gift, Package, Users, HeartHandshake, Camera, ArrowRight } from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";

export const Route = createFileRoute("/donor/dashboard")({
  head: () => ({ meta: [{ title: "Donor Dashboard — Donate" }] }),
  component: Dashboard,
});

const COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
  "var(--primary-dark)",
];

function Dashboard() {
  const { user } = useApp();
  return (
    <DashboardShell role="donor">
      <PageHeader
        title={`Welcome back, ${user?.name?.split(" ")[0] ?? "Donor"}`}
        subtitle="Here's your donation impact at a glance."
        action={
          <Button asChild className="gap-2">
            <Link to="/donor/donate">
              <Camera className="h-4 w-4" /> Start New Donation
            </Link>
          </Button>
        }
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Donations" value={12} icon={Gift} />
        <StatCard label="Items Donated" value={148} icon={Package} tone="secondary" />
        <StatCard label="NGOs Supported" value={7} icon={HeartHandshake} tone="accent" />
        <StatCard label="People Impacted" value="1,240" icon={Users} tone="success" />
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <SectionCard title="Donations by Category" className="lg:col-span-1">
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie
                data={CATEGORY_CHART}
                dataKey="value"
                nameKey="name"
                innerRadius={50}
                outerRadius={80}
                paddingAngle={2}
              >
                {CATEGORY_CHART.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </SectionCard>
        <SectionCard title="Monthly Donations" className="lg:col-span-2">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={MONTHLY_CHART}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
              <XAxis dataKey="month" tickLine={false} axisLine={false} fontSize={12} />
              <YAxis tickLine={false} axisLine={false} fontSize={12} />
              <Tooltip />
              <Bar dataKey="donations" fill="var(--primary)" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </SectionCard>
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <SectionCard
          title="Active Donations"
          className="lg:col-span-2"
          action={
            <Button asChild variant="ghost" size="sm" className="gap-1">
              <Link to="/donor/donations">
                View all <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          }
        >
          <div className="space-y-3">
            {DONATIONS.slice(0, 3).map((d) => (
              <div
                key={d.id}
                className="flex items-center justify-between rounded-lg border border-border p-3"
              >
                <div>
                  <p className="text-sm font-medium text-foreground">
                    {d.id} · {d.ngoName}
                  </p>
                  <p className="text-xs text-muted-foreground">{d.items.length} item types</p>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={d.status} />
                  <Button asChild size="sm" variant="outline">
                    <Link to="/donor/track/$id" params={{ id: d.id }}>
                      Track
                    </Link>
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
        <SectionCard title="Recommended NGOs">
          <div className="space-y-3">
            {NGOS.slice(0, 3).map((n) => (
              <div key={n.id} className="flex items-center gap-3">
                <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
                  <HeartHandshake className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">{n.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {n.city} · {n.activeDemands} demands
                  </p>
                </div>
                <StatusBadge status={n.priority} />
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </DashboardShell>
  );
}

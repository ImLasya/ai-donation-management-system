import { createFileRoute } from "@tanstack/react-router";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, StatCard, SectionCard } from "@/components/shared/ui";
import { Card } from "@/components/ui/card";
import { CATEGORY_CHART, MONTHLY_CHART } from "@/data/mock";
import { Gift, Package, HeartHandshake, Users, Award, Flame } from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

export const Route = createFileRoute("/donor/impact")({
  head: () => ({ meta: [{ title: "My Impact — Donate" }] }),
  component: Impact,
});

const BADGES = [
  { icon: Gift, label: "First Donation", earned: true },
  { icon: Flame, label: "5-Week Streak", earned: true },
  { icon: HeartHandshake, label: "5 NGOs Helped", earned: true },
  { icon: Award, label: "100 Items Milestone", earned: true },
  { icon: Users, label: "1,000 Beneficiaries", earned: false },
];

function Impact() {
  return (
    <DashboardShell role="donor">
      <PageHeader title="My Impact" subtitle="See the difference your donations make." />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Donations" value={12} icon={Gift} />
        <StatCard label="Total Items" value={148} icon={Package} tone="secondary" />
        <StatCard label="NGOs Supported" value={7} icon={HeartHandshake} tone="accent" />
        <StatCard
          label="Beneficiaries"
          value="1,240"
          icon={Users}
          tone="success"
          hint="estimated"
        />
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <SectionCard title="Monthly Donations">
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={MONTHLY_CHART}>
              <defs>
                <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--primary)" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="var(--primary)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
              <XAxis dataKey="month" tickLine={false} axisLine={false} fontSize={12} />
              <YAxis tickLine={false} axisLine={false} fontSize={12} />
              <Tooltip />
              <Area dataKey="donations" stroke="var(--primary)" fill="url(#g)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </SectionCard>
        <SectionCard title="Category Distribution">
          <div className="space-y-3">
            {CATEGORY_CHART.map((c) => (
              <div key={c.name}>
                <div className="mb-1 flex justify-between text-sm">
                  <span className="text-foreground">{c.name}</span>
                  <span className="text-muted-foreground">{c.value}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${(c.value / 40) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
      <SectionCard title="Achievements" className="mt-6">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {BADGES.map((b) => (
            <div
              key={b.label}
              className={`flex flex-col items-center gap-2 rounded-xl border p-4 text-center ${b.earned ? "border-primary/30 bg-primary/5" : "border-border opacity-50"}`}
            >
              <div
                className={`grid h-11 w-11 place-items-center rounded-full ${b.earned ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"}`}
              >
                <b.icon className="h-5 w-5" />
              </div>
              <span className="text-xs font-medium text-foreground">{b.label}</span>
            </div>
          ))}
        </div>
      </SectionCard>
    </DashboardShell>
  );
}

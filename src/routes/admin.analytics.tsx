import { createFileRoute } from "@tanstack/react-router";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, StatCard, SectionCard } from "@/components/shared/ui";
import { MONTHLY_CHART, CATEGORY_CHART } from "@/data/mock";
import { TrendingUp, Sparkles, Users, Gift } from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  BarChart,
  Bar,
} from "recharts";

export const Route = createFileRoute("/admin/analytics")({
  head: () => ({ meta: [{ title: "Analytics — Donate" }] }),
  component: Analytics,
});

function Analytics() {
  return (
    <DashboardShell role="admin">
      <PageHeader title="Analytics" subtitle="Platform trends and performance." />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Match Success Rate" value="92%" icon={Sparkles} tone="success" />
        <StatCard label="Avg. Match Time" value="1.4s" icon={TrendingUp} />
        <StatCard label="Monthly Growth" value="+18%" icon={Gift} tone="secondary" />
        <StatCard label="Active Users" value="6,120" icon={Users} tone="accent" />
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <SectionCard title="Monthly Donation Trends">
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={MONTHLY_CHART}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
              <XAxis dataKey="month" tickLine={false} axisLine={false} fontSize={12} />
              <YAxis tickLine={false} axisLine={false} fontSize={12} />
              <Tooltip />
              <Line dataKey="donations" stroke="var(--primary)" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </SectionCard>
        <SectionCard title="Donations by Category">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={CATEGORY_CHART}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
              <XAxis dataKey="name" tickLine={false} axisLine={false} fontSize={11} />
              <YAxis tickLine={false} axisLine={false} fontSize={12} />
              <Tooltip />
              <Bar dataKey="value" fill="var(--secondary)" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </SectionCard>
      </div>
    </DashboardShell>
  );
}

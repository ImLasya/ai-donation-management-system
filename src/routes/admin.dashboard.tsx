import { createFileRoute } from "@tanstack/react-router";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, StatCard, StatusBadge, SectionCard } from "@/components/shared/ui";
import { DONATIONS, NGOS, CATEGORY_CHART, DEMAND_SUPPLY } from "@/data/mock";
import { Gift, Package, Building2, Users, Sparkles, Truck } from "lucide-react";
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
  Legend,
} from "recharts";

export const Route = createFileRoute("/admin/dashboard")({
  head: () => ({ meta: [{ title: "Admin Dashboard — Donate" }] }),
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
  return (
    <DashboardShell role="admin">
      <PageHeader title="Platform Overview" subtitle="System-wide donation and matching metrics." />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Donations" value="12,480" icon={Gift} />
        <StatCard label="Items Donated" value="48,200" icon={Package} tone="secondary" />
        <StatCard label="Active NGOs" value={NGOS.length * 248} icon={Building2} tone="accent" />
        <StatCard label="Registered Donors" value="9,640" icon={Users} tone="success" />
        <StatCard label="Successful Matches" value="11,120" icon={Sparkles} />
        <StatCard label="Pending Pickups" value="342" icon={Truck} tone="secondary" />
        <StatCard label="Match Success Rate" value="92%" icon={Sparkles} tone="success" />
        <StatCard label="Beneficiaries" value="310K" icon={Users} tone="accent" />
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <SectionCard title="Donations by Category">
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
        <SectionCard title="Demand vs Supply" className="lg:col-span-2">
          <ResponsiveContainer width="100%" height={240}>
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
      </div>
      <SectionCard title="Recent Donations" className="mt-6">
        <div className="space-y-3">
          {DONATIONS.map((d) => (
            <div
              key={d.id}
              className="flex items-center justify-between rounded-lg border border-border p-3"
            >
              <div>
                <p className="text-sm font-medium text-foreground">
                  {d.id} · {d.ngoName}
                </p>
                <p className="text-xs text-muted-foreground">{d.date}</p>
              </div>
              <StatusBadge status={d.status} />
            </div>
          ))}
        </div>
      </SectionCard>
    </DashboardShell>
  );
}

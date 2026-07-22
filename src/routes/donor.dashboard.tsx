import { createFileRoute, Link } from "@tanstack/react-router";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, StatCard, StatusBadge, SectionCard } from "@/components/shared/ui";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useApp } from "@/context/AppContext";
import { donationService, type DonorImpactResponse } from "@/services";
import { NGOS } from "@/data/mock";
import { Gift, Package, Users, HeartHandshake, Camera, ArrowRight } from "lucide-react";
import { useEffect, useState } from "react";
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
  const [impact, setImpact] = useState<DonorImpactResponse | null>(null);
  const [donations, setDonations] = useState<any[]>([]);
  const [dbStats, setDbStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadDashboardData = async () => {
      setLoading(true);
      try {
        const [impactData, listData, statsData] = await Promise.all([
          donationService.getImpactAnalytics(),
          donationService.list(),
          donationService.getDonorDashboardStats(),
        ]);
        setImpact(impactData);
        setDonations(listData);
        setDbStats(statsData);
      } catch (err) {
        console.error("Failed to load donor dashboard database data:", err);
      } finally {
        setLoading(false);
      }
    };
    loadDashboardData();
  }, []);

  // Map backend category format to PieChart format
  const categoryChartData = impact?.categoryDistribution.map((c) => ({
    name: c.category,
    value: c.quantity,
  })) || [];

  // Map backend monthly format to BarChart format
  const monthlyChartData = impact?.monthlyDonations.map((m) => ({
    month: m.month,
    donations: m.count,
    year: m.year,
  })) || [];

  const summary = impact?.summary || {
    totalDonations: 0,
    totalItemsDonated: 0,
    ngosHelped: 0,
    beneficiariesReached: 0,
    beneficiariesIsEstimated: true,
    beneficiariesEstimationMethod: "total_items_donated * 3",
  };

  // Helper to determine the contextual action for a donation based on status
  const renderDonationAction = (d: any) => {
    if (d.status === "ITEMS_SUBMITTED" || d.status === "WAITING_FOR_MATCH") {
      return (
        <Button asChild size="sm">
          <Link to="/donor/matches">View Matches</Link>
        </Button>
      );
    }
    if (d.status === "NGO_ACCEPTED" || d.status === "PACKAGING_IN_PROGRESS") {
      return (
        <Button asChild size="sm" variant="default" className="bg-orange-600 hover:bg-orange-700">
          <Link to="/donor/packaging">Package Items</Link>
        </Button>
      );
    }
    if (d.status === "READY_FOR_PICKUP") {
      return (
        <Button asChild size="sm" variant="default" className="bg-teal-600 hover:bg-teal-700">
          <Link to="/donor/schedule">Schedule Pickup</Link>
        </Button>
      );
    }
    return (
      <Button asChild size="sm" variant="outline">
        <Link to="/donor/track/$id" params={{ id: d.id }}>Track</Link>
      </Button>
    );
  };

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
        {loading ? (
          [1, 2, 3, 4].map((i) => (
            <Card key={i} className="p-5 flex justify-between items-start">
              <div className="space-y-2 w-full">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-8 w-12" />
              </div>
              <Skeleton className="h-11 w-11 rounded-xl shrink-0" />
            </Card>
          ))
        ) : (
          <>
            <StatCard label="Total Donations" value={summary.totalDonations} icon={Gift} />
            <StatCard label="Items Donated" value={summary.totalItemsDonated} icon={Package} tone="secondary" />
            <StatCard label="NGOs Supported" value={summary.ngosHelped} icon={HeartHandshake} tone="accent" />
            <StatCard
              label="People Impacted"
              value={summary.beneficiariesReached ?? 0}
              icon={Users}
              tone="success"
              hint={summary.beneficiariesIsEstimated ? "estimated" : undefined}
            />
          </>
        )}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <SectionCard title="Donations by Category" className="lg:col-span-1">
          {loading ? (
            <div className="flex items-center justify-center h-[240px]">
              <Skeleton className="h-40 w-40 rounded-full" />
            </div>
          ) : categoryChartData.length === 0 ? (
            <div className="flex h-[240px] items-center justify-center text-sm text-muted-foreground">
              No categories recorded.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={categoryChartData}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={2}
                >
                  {categoryChartData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </SectionCard>

        <SectionCard title="Monthly Donations" className="lg:col-span-2">
          {loading ? (
            <div className="flex flex-col justify-end gap-2 h-[240px] w-full p-2">
              <Skeleton className="h-[200px] w-full" />
            </div>
          ) : monthlyChartData.length === 0 ? (
            <div className="flex h-[240px] items-center justify-center text-sm text-muted-foreground">
              No monthly donation history.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={monthlyChartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                <XAxis dataKey="month" tickLine={false} axisLine={false} fontSize={12} />
                <YAxis allowDecimals={false} tickLine={false} axisLine={false} fontSize={12} />
                <Tooltip labelFormatter={(label, payload) => {
                  if (payload && payload[0]) {
                    const point = payload[0].payload;
                    return `${point.month} ${point.year}`;
                  }
                  return label;
                }} />
                <Bar dataKey="donations" fill="var(--primary)" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </SectionCard>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <SectionCard
          title="Active Donations & Quick Actions"
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
            {loading ? (
              [1, 2, 3].map((i) => (
                <div key={i} className="flex justify-between items-center border border-border rounded-lg p-3">
                  <div className="space-y-2 w-full">
                    <Skeleton className="h-4 w-40" />
                    <Skeleton className="h-3 w-20" />
                  </div>
                  <Skeleton className="h-8 w-20 shrink-0" />
                </div>
              ))
            ) : donations.length === 0 ? (
              <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
                No active donations. Start a new donation above!
              </div>
            ) : (
              donations.slice(0, 3).map((d) => (
                <div
                  key={d.id}
                  className="flex items-center justify-between rounded-lg border border-border p-3"
                >
                  <div>
                    <p className="text-sm font-semibold text-foreground">
                      DON-{d.id} · {d.ngoName}
                    </p>
                    <p className="text-xs text-muted-foreground">{d.items?.length || 0} items</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusBadge status={d.status} />
                    {renderDonationAction(d)}
                  </div>
                </div>
              ))
            )}
          </div>
        </SectionCard>

        <div className="space-y-6">
          <SectionCard title="Upcoming Pickups">
            <div className="space-y-3">
              {loading ? (
                <Skeleton className="h-20 w-full" />
              ) : !dbStats?.upcomingPickups || dbStats.upcomingPickups.length === 0 ? (
                <div className="text-sm text-muted-foreground py-2 text-center">
                  No upcoming scheduled pickups.
                </div>
              ) : (
                dbStats.upcomingPickups.map((p: any, idx: number) => (
                  <div key={idx} className="rounded-lg border border-border p-3 space-y-1">
                    <p className="text-sm font-medium text-foreground">DON-{p.donationId} · {p.ngoName}</p>
                    <p className="text-xs text-muted-foreground">
                      <strong>Date:</strong> {p.date} · <strong>Time:</strong> {p.timeSlot}
                    </p>
                    <p className="text-xs text-muted-foreground truncate">
                      <strong>Address:</strong> {p.address}
                    </p>
                  </div>
                ))
              )}
            </div>
          </SectionCard>

          <SectionCard title="Recent Activity">
            <div className="space-y-3">
              {loading ? (
                <Skeleton className="h-20 w-full" />
              ) : !dbStats?.recentActivity || dbStats.recentActivity.length === 0 ? (
                <div className="text-sm text-muted-foreground py-2 text-center">
                  No recent activities recorded.
                </div>
              ) : (
                dbStats.recentActivity.map((a: any, idx: number) => (
                  <div key={idx} className="flex flex-col border-b border-border pb-2 last:border-0 last:pb-0">
                    <span className="text-xs text-muted-foreground">{a.timestamp}</span>
                    <span className="text-sm font-medium text-foreground">
                      DON-{a.donationId} transitioned to {a.newStatus.replace(/_/g, " ")}
                    </span>
                    {a.note && <span className="text-xs text-muted-foreground italic mt-0.5">"{a.note}"</span>}
                  </div>
                ))
              )}
            </div>
          </SectionCard>
        </div>
      </div>
    </DashboardShell>
  );
}

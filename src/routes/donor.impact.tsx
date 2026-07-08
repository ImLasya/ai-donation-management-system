import { createFileRoute } from "@tanstack/react-router";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, StatCard, SectionCard } from "@/components/shared/ui";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { donationService, type DonorImpactResponse } from "@/services";
import { Gift, Package, HeartHandshake, Users, Award, Flame, AlertCircle } from "lucide-react";
import { useEffect, useState } from "react";
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

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  FIRST_DONATION: Gift,
  STREAK_5_WEEK: Flame,
  HELPED_5_NGOS: HeartHandshake,
  ITEMS_100_MILESTONE: Award,
  BENEFICIARIES_1000: Users,
};

function Impact() {
  const [data, setData] = useState<DonorImpactResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const loadImpactData = async () => {
    setLoading(true);
    setError(false);
    try {
      const res = await donationService.getImpactAnalytics();
      setData(res);
    } catch (err) {
      console.error("Failed to load donor impact data:", err);
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadImpactData();
  }, []);

  if (error) {
    return (
      <DashboardShell role="donor">
        <PageHeader title="My Impact" subtitle="See the difference your donations make." />
        <Card className="mt-8 flex flex-col items-center justify-center gap-4 border-destructive/20 bg-destructive/5 p-12 text-center">
          <AlertCircle className="h-10 w-10 text-destructive" />
          <div>
            <h3 className="text-lg font-bold text-foreground">Unable to load impact analytics.</h3>
            <p className="text-sm text-muted-foreground mt-1">
              There was a problem connecting to the server. Please check your connection and try again.
            </p>
          </div>
          <Button onClick={loadImpactData} variant="outline" className="mt-2">
            Retry
          </Button>
        </Card>
      </DashboardShell>
    );
  }

  if (loading) {
    return (
      <DashboardShell role="donor">
        <PageHeader title="My Impact" subtitle="See the difference your donations make." />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className="p-5 flex justify-between items-start">
              <div className="space-y-2 w-full">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-8 w-16" />
                <Skeleton className="h-3 w-32" />
              </div>
              <Skeleton className="h-11 w-11 rounded-xl shrink-0" />
            </Card>
          ))}
        </div>
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <Card className="p-5 space-y-4">
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-[260px] w-full" />
          </Card>
          <Card className="p-5 space-y-4">
            <Skeleton className="h-5 w-40" />
            <div className="space-y-4">
              {[1, 2, 3, 4].map((j) => (
                <div key={j} className="space-y-2">
                  <div className="flex justify-between">
                    <Skeleton className="h-4 w-20" />
                    <Skeleton className="h-4 w-8" />
                  </div>
                  <Skeleton className="h-2 w-full rounded-full" />
                </div>
              ))}
            </div>
          </Card>
        </div>
        <Card className="p-5 mt-6 space-y-4">
          <Skeleton className="h-5 w-32" />
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
            {[1, 2, 3, 4, 5].map((k) => (
              <Card key={k} className="p-4 flex flex-col items-center gap-2 text-center">
                <Skeleton className="h-11 w-11 rounded-full" />
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-3 w-16" />
              </Card>
            ))}
          </div>
        </Card>
      </DashboardShell>
    );
  }

  // Safe fallback if data is null (should not happen after loading success)
  const impact = data || {
    summary: {
      totalDonations: 0,
      totalItemsDonated: 0,
      ngosHelped: 0,
      beneficiariesReached: 0,
      beneficiariesIsEstimated: true,
      beneficiariesEstimationMethod: "total_items_donated * 3",
    },
    monthlyDonations: [],
    categoryDistribution: [],
    achievements: [],
  };

  const isEmpty = impact.summary.totalDonations === 0;
  const maxCategoryQty = Math.max(...impact.categoryDistribution.map((c) => c.quantity), 1);

  return (
    <DashboardShell role="donor">
      <PageHeader title="My Impact" subtitle="See the difference your donations make." />
      
      {isEmpty && (
        <Card className="mb-6 border-primary/20 bg-primary/5 p-6 text-center sm:text-left flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <h4 className="font-bold text-foreground">Welcome to your Impact Journey!</h4>
            <p className="text-sm text-muted-foreground mt-1">
              Complete your first donation to start building your impact, unlocking badges, and supporting verified NGOs.
            </p>
          </div>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Donations" value={impact.summary.totalDonations} icon={Gift} />
        <StatCard label="Total Items" value={impact.summary.totalItemsDonated} icon={Package} tone="secondary" />
        <StatCard label="NGOs Supported" value={impact.summary.ngosHelped} icon={HeartHandshake} tone="accent" />
        <StatCard
          label="Beneficiaries"
          value={impact.summary.beneficiariesReached ?? 0}
          icon={Users}
          tone="success"
          hint={
            impact.summary.beneficiariesIsEstimated
              ? `Estimated: ${impact.summary.beneficiariesEstimationMethod || "total_items_donated * 3"}`
              : undefined
          }
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <SectionCard title="Monthly Donations">
          {isEmpty ? (
            <div className="flex h-[260px] items-center justify-center text-sm text-muted-foreground">
              No donation activity recorded.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={impact.monthlyDonations}>
                <defs>
                  <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--primary)" stopOpacity={0.4} />
                    <stop offset="100%" stopColor="var(--primary)" stopOpacity={0} />
                  </linearGradient>
                </defs>
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
                <Area dataKey="count" name="Donations" stroke="var(--primary)" fill="url(#g)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </SectionCard>

        <SectionCard title="Category Distribution">
          {impact.categoryDistribution.length === 0 ? (
            <div className="flex h-[260px] items-center justify-center text-sm text-muted-foreground">
              No items donated yet.
            </div>
          ) : (
            <div className="space-y-3 max-h-[260px] overflow-y-auto pr-1">
              {impact.categoryDistribution.map((c) => (
                <div key={c.category}>
                  <div className="mb-1 flex justify-between text-sm">
                    <span className="text-foreground">{c.category}</span>
                    <span className="text-muted-foreground font-medium">{c.quantity} {c.quantity === 1 ? "item" : "items"}</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-primary transition-all duration-500"
                      style={{ width: `${(c.quantity / maxCategoryQty) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      </div>

      <SectionCard title="Achievements" className="mt-6">
        {impact.achievements.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
            No achievements found.
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
            {impact.achievements.map((b) => {
              const Icon = ICON_MAP[b.key] || Award;
              return (
                <div
                  key={b.key}
                  className={`flex flex-col items-center gap-2 rounded-xl border p-4 text-center transition-all ${
                    b.unlocked
                      ? "border-primary/30 bg-primary/5 shadow-sm"
                      : "border-border opacity-50 bg-background/50"
                  }`}
                  title={`${b.description} (${b.progress}/${b.target})`}
                >
                  <div
                    className={`grid h-11 w-11 place-items-center rounded-full ${
                      b.unlocked
                        ? "bg-primary/10 text-primary animate-pulse"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    <Icon className="h-5 w-5" />
                  </div>
                  <span className="text-xs font-semibold text-foreground leading-tight">{b.title}</span>
                  <span className="text-[10px] text-muted-foreground leading-none">
                    {b.progress} / {b.target}
                  </span>
                  {b.unlocked_at && (
                    <span className="text-[8px] text-primary/70 font-medium leading-none mt-1">
                      Unlocked {new Date(b.unlocked_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </SectionCard>
    </DashboardShell>
  );
}

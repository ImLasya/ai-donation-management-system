import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, StatCard, StatusBadge, SectionCard } from "@/components/shared/ui";
import { Button } from "@/components/ui/button";
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

interface DashboardStats {
  activeDemands: number;
  highPriority: number;
  incomingDonations: number;
  beneficiaries: number;
  demandSupply: Array<{ month: string; demand: number; supply: number }>;
  urgentNeeds: Array<{ id: string; itemName: string; quantityRequired: number; quantityFulfilled: number; priority: string }>;
  recentDonations: Array<{ id: string; status: string; date: string; items: Array<{ id: string; itemName: string; quantity: number }> }>;
  compatibleMatches: Array<{ id: string; donationId: string; donorName: string; finalScore: number; date: string; items: Array<{ id: string; itemName: string; quantity: number }> }>;
  acceptedDonations: Array<{ id: string; status: string; donorName: string; date: string; itemCount: number }>;
  upcomingPickups: Array<{ donationId: string; date: string; timeSlot: string; address: string; phone: string; donorName: string }>;
  expiringDemands: Array<{ id: string; title: string; expiryDate: string }>;
  completedDonationHistory: Array<{ id: string; donorName: string; date: string; completedDate: string; itemCount: number }>;
  notifications: Array<{ id: string; title: string; message: string; isRead: boolean; date: string }>;
}

function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const token = localStorage.getItem("da_token");
        const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/donations/ngo/dashboard-stats`, {
          headers: {
            Authorization: `Bearer ${token}`
          }
        });
        if (res.ok) {
          const data = await res.json();
          setStats(data);
        }
      } catch (err) {
        console.error("Failed to load dashboard stats", err);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  if (loading) {
    return (
      <DashboardShell role="ngo">
        <PageHeader title="NGO Dashboard" subtitle="Loading metrics..." />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 rounded-lg bg-muted animate-pulse" />
          ))}
        </div>
      </DashboardShell>
    );
  }

  const activeDemands = stats?.activeDemands ?? 0;
  const highPriority = stats?.highPriority ?? 0;
  const incomingDonations = stats?.incomingDonations ?? 0;
  const beneficiaries = stats?.beneficiaries ?? 0;

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
        <StatCard label="Active Demands" value={activeDemands} icon={ClipboardList} />
        <StatCard label="High Priority Needs" value={highPriority} icon={Flame} tone="accent" />
        <StatCard
          label="Incoming Requests"
          value={incomingDonations}
          icon={Truck}
          tone="secondary"
          className="cursor-pointer hover:bg-muted/10 transition-colors"
          asChild
        >
          <Link to="/ngo/incoming" />
        </StatCard>
        <StatCard label="Beneficiaries Impacted" value={beneficiaries.toLocaleString()} icon={Users} tone="success" />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <SectionCard title="Demand vs Supply Trend" className="lg:col-span-2">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={stats?.demandSupply ?? []}>
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

        <SectionCard title="Urgent Demand Needs">
          <div className="space-y-3">
            {stats?.urgentNeeds && stats.urgentNeeds.length > 0 ? (
              stats.urgentNeeds.map((d) => (
                <div
                  key={d.id}
                  className="flex items-center justify-between rounded-lg border border-border p-3"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-foreground">{d.itemName}</p>
                    <p className="text-xs text-muted-foreground">
                      Fulfillment: {d.quantityFulfilled} of {d.quantityRequired} required
                    </p>
                  </div>
                  <StatusBadge status={d.priority} />
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground p-3 text-center">No urgent needs registered.</p>
            )}
          </div>
        </SectionCard>
      </div>

      {/* Grid: Active Donations & Upcoming Pickups */}
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <SectionCard
          title="Accepted & Active Donations"
          action={
            <Button asChild variant="ghost" size="sm" className="gap-1">
              <Link to="/ngo/incoming">
                Manage Active <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          }
        >
          <div className="space-y-3">
            {stats?.acceptedDonations && stats.acceptedDonations.length > 0 ? (
              stats.acceptedDonations.map((d) => (
                <div key={d.id} className="flex items-center justify-between rounded-lg border border-border p-3">
                  <div>
                    <p className="text-sm font-semibold text-foreground">DON-{d.id} · {d.donorName}</p>
                    <p className="text-xs text-muted-foreground">{d.itemCount} items · Date: {d.date}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={d.status} />
                    <Button asChild size="sm" variant="outline">
                      <Link to="/donor/track/$id" params={{ id: d.id }}>Track</Link>
                    </Button>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground py-6 text-center">No accepted or active donations at this time.</p>
            )}
          </div>
        </SectionCard>

        <SectionCard title="Upcoming Pickups (NGO Schedule)">
          <div className="space-y-3">
            {stats?.upcomingPickups && stats.upcomingPickups.length > 0 ? (
              stats.upcomingPickups.map((p, idx) => (
                <div key={idx} className="rounded-lg border border-border p-3 space-y-1">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-foreground">DON-{p.donationId} · {p.donorName}</p>
                    <span className="text-xs font-semibold text-primary">{p.date} · {p.timeSlot}</span>
                  </div>
                  <p className="text-xs text-muted-foreground"><strong>Address:</strong> {p.address}</p>
                  <p className="text-xs text-muted-foreground"><strong>Phone:</strong> {p.phone}</p>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground py-6 text-center">No scheduled pickups for tomorrow or upcoming days.</p>
            )}
          </div>
        </SectionCard>
      </div>

      {/* Grid: Compatible Matches & Expiring Demands / Notifications */}
      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <SectionCard title="Compatible Matches (Vector Scored)" className="lg:col-span-2">
          <div className="space-y-3">
            {stats?.compatibleMatches && stats.compatibleMatches.length > 0 ? (
              stats.compatibleMatches.map((m) => (
                <div key={m.id} className="flex items-center justify-between rounded-lg border border-border p-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold text-foreground">DON-{m.donationId} · {m.donorName}</p>
                      <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary font-bold">
                        {m.finalScore}% Match
                      </span>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {m.items.map((it, idx) => (
                        <span key={idx} className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                          {it.itemName} (x{it.quantity})
                        </span>
                      ))}
                    </div>
                  </div>
                  <Button asChild size="sm">
                    <Link to="/ngo/incoming">View Details</Link>
                  </Button>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground py-6 text-center">No automatic vector matches computed yet.</p>
            )}
          </div>
        </SectionCard>

        <div className="space-y-6 lg:col-span-1">
          <SectionCard title="Expiring Demands">
            <div className="space-y-3">
              {stats?.expiringDemands && stats.expiringDemands.length > 0 ? (
                stats.expiringDemands.map((d) => (
                  <div key={d.id} className="flex items-center justify-between rounded-lg border border-border p-3">
                    <p className="text-sm font-semibold text-foreground truncate">{d.title}</p>
                    <span className="text-xs bg-red-50 text-red-600 font-bold px-2 py-0.5 rounded-full">{d.expiryDate}</span>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground py-2 text-center">No expiring demands found.</p>
              )}
            </div>
          </SectionCard>

          <SectionCard title="Recent Notifications">
            <div className="space-y-3">
              {stats?.notifications && stats.notifications.length > 0 ? (
                stats.notifications.map((n) => (
                  <div key={n.id} className="flex flex-col border-b border-border pb-2 last:border-0 last:pb-0">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold text-foreground">{n.title}</span>
                      <span className="text-xs text-muted-foreground">{n.date}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">{n.message}</p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground py-2 text-center">No recent alerts.</p>
              )}
            </div>
          </SectionCard>
        </div>
      </div>

      {/* Completed Donation History */}
      <SectionCard title="Completed Donation History (Past Receipts)" className="mt-6">
        <div className="space-y-3">
          {stats?.completedDonationHistory && stats.completedDonationHistory.length > 0 ? (
            stats.completedDonationHistory.map((h) => (
              <div key={h.id} className="flex items-center justify-between rounded-lg border border-border p-3">
                <div>
                  <p className="text-sm font-semibold text-foreground">DON-{h.id} · {h.donorName}</p>
                  <p className="text-xs text-muted-foreground">
                    Items: {h.itemCount} · Date: {h.date} · Completed: {h.completedDate}
                  </p>
                </div>
                <span className="rounded-full bg-green-50 px-2 py-0.5 text-xs text-green-700 font-bold border border-green-200">
                  Acknowledged
                </span>
              </div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground py-6 text-center">No completed donations in your history archive.</p>
          )}
        </div>
      </SectionCard>
    </DashboardShell>
  );
}

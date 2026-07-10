import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, StatusBadge } from "@/components/shared/ui";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Search, ArrowRight } from "lucide-react";
import { useApp } from "@/context/AppContext";

export const Route = createFileRoute("/donor/donations")({
  head: () => ({ meta: [{ title: "My Donations — Donate" }] }),
  component: Donations,
});

function Donations() {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("all");
  const [donations, setDonations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const { setDraft } = useApp();

  useEffect(() => {
    const fetchDonations = async () => {
      try {
        const token = localStorage.getItem("da_token");
        const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/donations/list`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        if (res.ok) {
          const data = await res.json();
          setDonations(data);
        }
      } catch (err) {
        console.error("Failed to load donations:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchDonations();
  }, []);

  const getStatusLabel = (d: any): string => {
    if (d.status === "WAITING_FOR_MATCH") {
      return "Waiting for NGO Match";
    }
    if (d.status === "ITEMS_SUBMITTED") {
      return d.has_available_matches ? "New Match Available" : "Items Submitted";
    }
    if (d.status === "EXPIRED") {
      return "Expired";
    }
    const mapping: Record<string, string> = {
      DRAFT: "Draft",
      PENDING_NGO_RESPONSE: "Awaiting NGO",
      NGO_ACCEPTED: "Accepted",
      PACKAGING_IN_PROGRESS: "Packaging",
      READY_FOR_PICKUP: "Ready for Pickup",
      PICKUP_SCHEDULED: "Pickup Scheduled",
      PICKUP_IN_PROGRESS: "Pickup In Progress",
      COMPLETED: "Completed",
      NGO_REJECTED: "Declined"
    };
    return mapping[d.status] || d.status;
  };

  const list = donations.filter(
    (d) => {
      const displayStatus = getStatusLabel(d);
      return (status === "all" || displayStatus === status) &&
        (d.ngoName.toLowerCase().includes(q.toLowerCase()) ||
          d.id.toLowerCase().includes(q.toLowerCase()));
    }
  );

  return (
    <DashboardShell role="donor">
      <PageHeader
        title="My Donations"
        subtitle="Search, filter, and track your donation history."
      />
      <div className="mb-5 flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-52">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search donations…"
            className="pl-9"
          />
        </div>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="w-56">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {[
              "Waiting for NGO Match",
              "New Match Available",
              "Items Submitted",
              "Awaiting NGO",
              "Accepted",
              "Packaging",
              "Ready for Pickup",
              "Pickup Scheduled",
              "Pickup In Progress",
              "Completed",
              "Declined",
              "Expired",
            ].map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="grid gap-4">
        {loading ? (
          <div className="text-center py-8 text-muted-foreground">Loading donations...</div>
        ) : list.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">No donations found.</div>
        ) : (
          list.map((d) => (
            <Card
              key={d.id}
              className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-semibold text-foreground">#{d.id}</p>
                  <StatusBadge status={getStatusLabel(d)} />
                </div>
                <p className="mt-1 text-sm text-muted-foreground">
                  {d.ngoName} · {d.date}
                </p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {d.items.map((it: any) => (
                    <span
                      key={it.id}
                      className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground"
                    >
                      {it.label} ×{it.quantity}
                    </span>
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-4 sm:flex-col sm:items-end">
                <span className="text-sm text-muted-foreground">{d.beneficiaries} helped</span>
                <div className="flex gap-2">
                  {d.status === "ITEMS_SUBMITTED" && d.has_available_matches && (
                    <Button
                      onClick={() => {
                        setDraft({ donationId: Number(d.id) });
                      }}
                      asChild
                      size="sm"
                      className="gap-1 bg-emerald-600 hover:bg-emerald-700 text-white"
                    >
                      <Link to="/donor/matches">
                        Select NGO <ArrowRight className="h-4 w-4" />
                      </Link>
                    </Button>
                  )}
                  <Button asChild size="sm" variant="outline" className="gap-1">
                    <Link to="/donor/track/$id" params={{ id: d.id }}>
                      Track <ArrowRight className="h-4 w-4" />
                    </Link>
                  </Button>
                </div>
              </div>
            </Card>
          ))
        )}
      </div>
    </DashboardShell>
  );
}

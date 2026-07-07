import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect, useCallback } from "react";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, StatusBadge, EmptyState } from "@/components/shared/ui";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Search,
  PlusCircle,
  Trash2,
  Pause,
  Play,
  ClipboardList,
  MapPin,
  Calendar,
  Package,
} from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/ngo/demands/")({
  head: () => ({ meta: [{ title: "Demand Registry — Donate" }] }),
  component: DemandsIndex,
});

interface DemandItem {
  id: string;
  item_name: string;
  category: string;
  quantity_needed: number;
  quantity_fulfilled: number;
  minimum_condition: string;
}

interface Demand {
  id: string;
  title: string;
  description: string;
  city: string;
  priority: string;
  status: string;
  db_status: string;
  expiryDate: string;
  createdAt: string;
  items: DemandItem[];
  // legacy compat
  itemName: string;
  category: string;
  quantityRequired: number;
  quantityFulfilled: number;
}

const PRIORITY_COLORS: Record<string, string> = {
  Low: "bg-slate-100 text-slate-700 border-slate-200",
  Medium: "bg-blue-50 text-blue-700 border-blue-200",
  High: "bg-orange-50 text-orange-700 border-orange-200",
  Urgent: "bg-red-50 text-red-700 border-red-200",
};

function DemandsIndex() {
  const navigate = useNavigate();
  const [demands, setDemands] = useState<Demand[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");

  const fetchDemands = useCallback(async () => {
    try {
      const token = localStorage.getItem("da_token");
      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/api/donations/demands/my`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.ok) {
        const data = await res.json();
        setDemands(data);
      } else {
        toast.error("Failed to load demand registry.");
      }
    } catch (err) {
      console.error("Failed to fetch demands:", err);
      toast.error("Network error while loading demands.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDemands();
  }, [fetchDemands]);

  const handleToggleStatus = async (id: string, currentStatus: string) => {
    const nextStatus = currentStatus === "Active" ? "Paused" : "Active";
    try {
      const token = localStorage.getItem("da_token");
      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/api/donations/demands/${id}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ status: nextStatus }),
        }
      );
      if (!res.ok) throw new Error("Failed to update status");
      toast.success(nextStatus === "Active" ? "Demand Reactivated" : "Demand Paused");
      fetchDemands();
    } catch {
      toast.error("Failed to update demand status");
    }
  };

  const handleDelete = async (id: string) => {
    try {
      const token = localStorage.getItem("da_token");
      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/api/donations/demands/${id}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (!res.ok) throw new Error("Failed to archive demand");
      toast.success("Demand closed");
      fetchDemands();
    } catch {
      toast.error("Failed to close demand");
    }
  };

  const lower = q.toLowerCase();
  const list = demands.filter(
    (d) =>
      d.title?.toLowerCase().includes(lower) ||
      d.itemName?.toLowerCase().includes(lower) ||
      d.city?.toLowerCase().includes(lower) ||
      d.items?.some(
        (it) =>
          it.item_name.toLowerCase().includes(lower) ||
          it.category.toLowerCase().includes(lower)
      )
  );

  return (
    <DashboardShell role="ngo">
      <PageHeader
        title="Demand Registry"
        subtitle="Maintain your live list of needed items."
        action={
          <Button
            id="create-demand-btn"
            className="gap-2"
            onClick={() => navigate({ to: "/ngo/demands/new" })}
          >
            <PlusCircle className="h-4 w-4" />
            Create Demand
          </Button>
        }
      />
      <div className="relative mb-5 max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search demands…"
          className="pl-9"
          id="demand-search-input"
        />
      </div>

      {loading ? (
        <div className="grid gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="p-5 animate-pulse">
              <div className="h-5 w-48 rounded bg-muted mb-3" />
              <div className="h-3 w-32 rounded bg-muted mb-2" />
              <div className="h-3 w-64 rounded bg-muted" />
            </Card>
          ))}
        </div>
      ) : list.length === 0 ? (
        <EmptyState
          icon={ClipboardList}
          title="No demands yet"
          message={
            q
              ? `No demands match "${q}". Try a different search term.`
              : "Start building your demand registry to match with incoming donations."
          }
          action={
            <Button
              id="create-first-demand-btn"
              onClick={() => navigate({ to: "/ngo/demands/new" })}
            >
              <PlusCircle className="mr-2 h-4 w-4" />
              Create your first demand
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4">
          {list.map((d) => {
            const paused = d.status === "Paused";
            const priorityClass =
              PRIORITY_COLORS[d.priority] ?? PRIORITY_COLORS["Medium"];
            const totalNeeded =
              d.items?.reduce((s, it) => s + it.quantity_needed, 0) ??
              d.quantityRequired;
            const totalFulfilled =
              d.items?.reduce((s, it) => s + it.quantity_fulfilled, 0) ??
              d.quantityFulfilled;
            const pct =
              totalNeeded > 0
                ? Math.round((totalFulfilled / totalNeeded) * 100)
                : 0;

            return (
              <Card
                key={d.id}
                className={`p-5 transition-opacity ${paused ? "opacity-60" : ""}`}
              >
                {/* Header row */}
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <h3 className="font-semibold text-foreground text-base leading-tight">
                        {d.title}
                      </h3>
                      <span
                        className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${priorityClass}`}
                      >
                        {d.priority}
                      </span>
                      <StatusBadge status={d.status} />
                    </div>

                    {/* Meta row */}
                    <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground mb-3">
                      {d.city && (
                        <span className="flex items-center gap-1">
                          <MapPin className="h-3 w-3" />
                          {d.city}
                        </span>
                      )}
                      {d.expiryDate && d.expiryDate !== "—" && (
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          Needed by {d.expiryDate}
                        </span>
                      )}
                    </div>

                    {d.description && (
                      <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                        {d.description}
                      </p>
                    )}

                    {/* Items list */}
                    {d.items && d.items.length > 0 && (
                      <div className="mb-3">
                        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-1">
                          <Package className="h-3 w-3" />
                          Needed Items ({d.items.length})
                        </p>
                        <div className="grid gap-1.5">
                          {d.items.map((it) => {
                            const itPct =
                              it.quantity_needed > 0
                                ? Math.round(
                                    (it.quantity_fulfilled /
                                      it.quantity_needed) *
                                      100
                                  )
                                : 0;
                            return (
                              <div
                                key={it.id}
                                className="flex items-center gap-3 rounded-md bg-muted/40 px-3 py-2 text-sm"
                              >
                                <div className="min-w-0 flex-1">
                                  <span className="font-medium text-foreground">
                                    {it.item_name}
                                  </span>
                                  <span className="ml-2 text-xs text-muted-foreground">
                                    {it.category}
                                  </span>
                                  {it.minimum_condition && (
                                    <span className="ml-2 text-xs text-muted-foreground">
                                      ·{" "}
                                      {it.minimum_condition.replace(/,/g, ", ")}
                                    </span>
                                  )}
                                </div>
                                <div className="shrink-0 text-right">
                                  <span className="font-medium text-foreground">
                                    {it.quantity_fulfilled}/{it.quantity_needed}
                                  </span>
                                  <div className="mt-1 h-1 w-20 rounded-full bg-muted overflow-hidden">
                                    <div
                                      className="h-full rounded-full bg-primary transition-all"
                                      style={{ width: `${itPct}%` }}
                                    />
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Overall progress */}
                    <div className="max-w-sm">
                      <div className="mb-1 flex justify-between text-xs">
                        <span className="text-muted-foreground">
                          Overall fulfillment
                        </span>
                        <span className="font-medium text-foreground">
                          {totalFulfilled}/{totalNeeded} ({pct}%)
                        </span>
                      </div>
                      <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full rounded-full bg-primary transition-all"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Action buttons */}
                  <div className="flex gap-1 shrink-0">
                    <Button
                      size="icon"
                      variant="ghost"
                      aria-label={paused ? "Reactivate" : "Pause"}
                      id={`toggle-demand-${d.id}`}
                      onClick={() => handleToggleStatus(d.id, d.status)}
                    >
                      {paused ? (
                        <Play className="h-4 w-4" />
                      ) : (
                        <Pause className="h-4 w-4" />
                      )}
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      aria-label="Close demand"
                      id={`delete-demand-${d.id}`}
                      onClick={() => handleDelete(d.id)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </DashboardShell>
  );
}

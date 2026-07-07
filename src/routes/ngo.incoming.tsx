import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, StatusBadge } from "@/components/shared/ui";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Check, X } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/ngo/incoming")({
  head: () => ({ meta: [{ title: "Incoming Donations — Donate" }] }),
  component: Incoming,
});

function Incoming() {
  const [requests, setRequests] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchRequests = async () => {
    try {
      const token = localStorage.getItem("da_token");
      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/api/donations/requests/incoming`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );
      if (res.ok) {
        const data = await res.json();
        setRequests(data);
      }
    } catch (err) {
      console.error("Failed to load incoming requests:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  const handleAccept = async (id: number) => {
    try {
      const token = localStorage.getItem("da_token");
      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/api/donations/requests/${id}/accept`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to accept request.");
      }

      toast.success("Donation request accepted successfully!");
      fetchRequests();
    } catch (err) {
      console.error(err);
      toast.error(err instanceof Error ? err.message : "Failed to accept request.");
    }
  };

  const handleReject = async (id: number) => {
    try {
      const token = localStorage.getItem("da_token");
      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/api/donations/requests/${id}/reject`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to reject request.");
      }

      toast.success("Donation request declined.");
      fetchRequests();
    } catch (err) {
      console.error(err);
      toast.error(err instanceof Error ? err.message : "Failed to reject request.");
    }
  };

  return (
    <DashboardShell role="ngo">
      <PageHeader title="Incoming Donations" subtitle="Review and coordinate matched donations." />
      <div className="grid gap-4">
        {loading ? (
          <p className="text-muted-foreground">Loading incoming requests...</p>
        ) : requests.length === 0 ? (
          <Card className="p-8 text-center border-dashed">
            <p className="text-muted-foreground font-medium">
              No incoming donation requests at the moment.
            </p>
          </Card>
        ) : (
          requests.map((r) => (
            <Card
              key={r.id}
              className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-semibold text-foreground">Request #{r.id}</p>
                  <StatusBadge status={r.status} />
                </div>
                <p className="mt-1 text-sm text-muted-foreground">
                  Donor: <span className="font-semibold text-foreground">{r.donorName}</span> ·
                  City: {r.donorCity} · Date: {r.date}
                </p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {r.items.map((it: any) => (
                    <span
                      key={it.id}
                      className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground"
                    >
                      {it.label} ×{it.quantity} ({it.condition})
                    </span>
                  ))}
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" className="gap-1" onClick={() => handleAccept(r.id)}>
                  <Check className="h-4 w-4" /> Accept
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="gap-1"
                  onClick={() => handleReject(r.id)}
                >
                  <X className="h-4 w-4" /> Decline
                </Button>
              </div>
            </Card>
          ))
        )}
      </div>
    </DashboardShell>
  );
}

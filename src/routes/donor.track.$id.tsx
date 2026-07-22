import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, EmptyState, StatusBadge } from "@/components/shared/ui";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useApp } from "@/context/AppContext";
import { cn } from "@/lib/utils";
import { CheckCircle2, Circle, Truck, ArrowRight } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/donor/track/$id")({
  head: () => ({ meta: [{ title: "Track Donation — Donate" }] }),
  component: Track,
});

function Track() {
  const { id } = Route.useParams();
  const { user } = useApp();
  const [donation, setDonation] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTrack = async () => {
      try {
        const token = localStorage.getItem("da_token");
        const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/donations/${id}/track`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        if (res.ok) {
          const data = await res.json();
          setDonation(data);
        }
      } catch (err) {
        console.error("Failed to load tracking details:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchTrack();
    const interval = setInterval(fetchTrack, 5000);
    return () => clearInterval(interval);
  }, [id]);

  const currentRole = (user?.role?.toLowerCase() || "donor") as any;

  if (loading) {
    return (
      <DashboardShell role={currentRole}>
        <div className="flex h-64 items-center justify-center">
          <p className="text-muted-foreground">Loading tracking timeline...</p>
        </div>
      </DashboardShell>
    );
  }

  if (!donation) {
    return (
      <DashboardShell role={currentRole}>
        <EmptyState title="Donation not found" />
      </DashboardShell>
    );
  }

  return (
    <DashboardShell role={currentRole}>
      <PageHeader
        title={`Track DON-${donation.id}`}
        subtitle={`Donation to ${donation.ngoName}`}
        action={<StatusBadge status={donation.status} />}
      />
      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="p-6 lg:col-span-2">
          <h3 className="mb-6 font-semibold text-foreground">Donation journey</h3>
          
          {/* Mobile view */}
          <ol className="relative space-y-6 border-l-2 border-border pl-6 md:hidden">
            {donation.events.map((e: any) => (
              <TimelineItem key={e.status} e={e} />
            ))}
          </ol>

          {/* Desktop view */}
          <div className="hidden md:block">
            <div className="flex items-center justify-between">
              {donation.events.map((e: any, i: number) => (
                <div key={e.status} className="flex flex-1 flex-col items-center text-center">
                  <div className="flex w-full items-center">
                    <div
                      className={cn(
                        "h-0.5 flex-1",
                        i === 0 ? "bg-transparent" : e.done ? "bg-primary" : "bg-border",
                      )}
                    />
                    {e.done ? (
                      <CheckCircle2 className="h-6 w-6 text-primary" />
                    ) : (
                      <Circle className="h-6 w-6 text-muted-foreground" />
                    )}
                    <div
                      className={cn(
                        "h-0.5 flex-1",
                        i === donation.events.length - 1
                          ? "bg-transparent"
                          : donation.events[i + 1]?.done
                            ? "bg-primary"
                            : "bg-border",
                      )}
                    />
                  </div>
                  <p className="mt-2 text-xs font-semibold text-foreground">{e.status}</p>
                  <p className="text-[11px] text-muted-foreground font-semibold mt-0.5">{e.timestamp}</p>
                </div>
              ))}
            </div>

            <div className="mt-8 space-y-3">
              {donation.events.map((e: any) => (
                <div key={e.status} className="flex items-start gap-2.5 text-sm">
                  {e.done ? (
                    <CheckCircle2 className="h-4 w-4 text-success mt-0.5 shrink-0" />
                  ) : (
                    <Circle className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                  )}
                  <div>
                    <span className={e.done ? "text-foreground font-semibold block" : "text-muted-foreground font-semibold block"}>
                      {e.status}
                    </span>
                    <span className="text-xs text-muted-foreground block">{e.description}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {currentRole === "donor" && (donation.status === "NGO_ACCEPTED" || donation.status === "PACKAGING_IN_PROGRESS") && (
            <Card className="mt-6 border-primary/20 bg-primary/5 p-6">
              <h3 className="font-semibold text-primary">
                {donation.status === "PACKAGING_IN_PROGRESS"
                  ? "Packaging In Progress"
                  : "Prepare your package"}
              </h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Your request was accepted! Prepare the items following our checklist so they arrive
                safely.
              </p>
              <Button asChild className="mt-4 gap-2">
                <Link to="/donor/packaging">
                  {donation.status === "PACKAGING_IN_PROGRESS"
                    ? "Continue Packaging Checklist"
                    : "Start Packaging Checklist"}{" "}
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            </Card>
          )}

          {currentRole === "donor" && donation.status === "READY_FOR_PICKUP" && (
            <Card className="mt-6 border-primary/20 bg-primary/5 p-6">
              <h3 className="font-semibold text-primary">Schedule Pickup</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Items are successfully packaged. Coordinate a convenient slot for collection.
              </p>
              <Button asChild className="mt-4 gap-2">
                <Link to="/donor/schedule">
                  Schedule Collection <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            </Card>
          )}
        </Card>

        <div className="space-y-6">
          <Card className="p-6">
            <h3 className="font-semibold text-foreground border-b border-border pb-2">Donation details</h3>
            <dl className="mt-4 space-y-2.5 text-sm">
              <Row label="NGO Partner" value={donation.ngoName} />
              <Row label="Submitted Date" value={donation.date} />
              <Row label="Pickup Scheduled" value={donation.pickup ? `${donation.pickup.date} (${donation.pickup.timeSlot})` : "—"} />
              <Row label="Beneficiaries" value={String(donation.beneficiaries)} />
            </dl>
            <div className="mt-4 border-t border-border pt-4">
              <p className="mb-2 text-xs font-bold uppercase text-muted-foreground">Items List</p>
              {donation.items.map((it: any) => (
                <div key={it.id} className="flex justify-between text-sm py-1 border-b border-border last:border-0">
                  <span className="text-foreground font-semibold">{it.label}</span>
                  <span className="text-muted-foreground font-semibold">×{it.quantity}</span>
                </div>
              ))}
            </div>
          </Card>

          <Card className="flex items-center gap-3 p-6">
            <Truck className="h-8 w-8 text-primary shrink-0" />
            <div>
              {donation.volunteer ? (
                <>
                  <p className="text-sm font-medium text-foreground">
                    Volunteer: {donation.volunteer.name}
                  </p>
                  <p className="text-xs text-muted-foreground">{donation.volunteer.phone}</p>
                </>
              ) : (
                <>
                  <p className="text-sm font-medium text-foreground">Volunteer Assignment</p>
                  <p className="text-xs text-muted-foreground">Volunteer not assigned yet.</p>
                </>
              )}
            </div>
          </Card>
          
          <Button asChild variant="outline" className="w-full">
            <Link to={currentRole === "ngo" ? "/ngo/incoming" : "/donor/donations"}>
              Back to List
            </Link>
          </Button>
        </div>
      </div>
    </DashboardShell>
  );
}

function TimelineItem({
  e,
}: {
  e: { status: string; description: string; timestamp: string; done: boolean };
}) {
  return (
    <li className="relative">
      <span
        className={cn(
          "absolute -left-[31px] grid h-5 w-5 place-items-center rounded-full",
          e.done ? "bg-primary text-primary-foreground" : "bg-muted",
        )}
      >
        {e.done ? (
          <CheckCircle2 className="h-4 w-4" />
        ) : (
          <Circle className="h-3 w-3 text-muted-foreground" />
        )}
      </span>
      <p className="text-sm font-semibold text-foreground">{e.status}</p>
      <p className="text-xs text-muted-foreground">
        {e.description} · <span className="font-semibold">{e.timestamp}</span>
      </p>
    </li>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-semibold text-foreground">{value}</dd>
    </div>
  );
}

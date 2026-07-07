import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, EmptyState, StatusBadge } from "@/components/shared/ui";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DONATIONS } from "@/data/mock";
import { cn } from "@/lib/utils";
import { CheckCircle2, Circle, Truck, ArrowRight } from "lucide-react";

export const Route = createFileRoute("/donor/track/$id")({
  head: () => ({ meta: [{ title: "Track Donation — Donate" }] }),
  component: Track,
});

function Track() {
  const { id } = Route.useParams();
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
  }, [id]);

  if (loading) {
    return (
      <DashboardShell role="donor">
        <div className="flex h-64 items-center justify-center">
          <p className="text-muted-foreground">Loading tracking timeline...</p>
        </div>
      </DashboardShell>
    );
  }

  if (!donation) {
    return (
      <DashboardShell role="donor">
        <EmptyState title="Donation not found" />
      </DashboardShell>
    );
  }

  return (
    <DashboardShell role="donor">
      <PageHeader
        title={`Track ${donation.id}`}
        subtitle={`Donation to ${donation.ngoName}`}
        action={<StatusBadge status={donation.status} />}
      />
      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="p-6 lg:col-span-2">
          <h3 className="mb-6 font-semibold text-foreground">Donation journey</h3>
          <ol className="relative space-y-6 border-l-2 border-border pl-6 md:hidden">
            {donation.events.map((e) => (
              <TimelineItem key={e.status} e={e} />
            ))}
          </ol>
          <div className="hidden md:block">
            <div className="flex items-center justify-between">
              {donation.events.map((e, i) => (
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
                  <p className="mt-2 text-xs font-medium text-foreground">{e.status}</p>
                  <p className="text-[11px] text-muted-foreground">{e.timestamp}</p>
                </div>
              ))}
            </div>
            <div className="mt-6 space-y-2">
              {donation.events.map((e) => (
                <div key={e.status} className="flex items-center gap-2 text-sm">
                  {e.done ? (
                    <CheckCircle2 className="h-4 w-4 text-success" />
                  ) : (
                    <Circle className="h-4 w-4 text-muted-foreground" />
                  )}
                  <span className={e.done ? "text-foreground" : "text-muted-foreground"}>
                    {e.description}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {(donation.status === "NGO_ACCEPTED" || donation.status === "PACKAGING_IN_PROGRESS") && (
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

          {donation.status === "READY_FOR_PICKUP" && (
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
            <h3 className="font-semibold text-foreground">Donation details</h3>
            <dl className="mt-4 space-y-2 text-sm">
              <Row label="NGO" value={donation.ngoName} />
              <Row label="Date" value={donation.date} />
              <Row label="Pickup" value={donation.pickupDate ?? "—"} />
              <Row label="Beneficiaries" value={String(donation.beneficiaries)} />
            </dl>
            <div className="mt-4 border-t border-border pt-4">
              <p className="mb-2 text-xs font-medium text-muted-foreground">Items</p>
              {donation.items.map((it) => (
                <div key={it.id} className="flex justify-between text-sm">
                  <span className="text-foreground">{it.label}</span>
                  <span className="text-muted-foreground">×{it.quantity}</span>
                </div>
              ))}
            </div>
          </Card>
          <Card className="flex items-center gap-3 p-6">
            <Truck className="h-8 w-8 text-primary" />
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
            <Link to="/donor/donations">All donations</Link>
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
      <p className="text-sm font-medium text-foreground">{e.status}</p>
      <p className="text-xs text-muted-foreground">
        {e.description} · {e.timestamp}
      </p>
    </li>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium text-foreground">{value}</dd>
    </div>
  );
}

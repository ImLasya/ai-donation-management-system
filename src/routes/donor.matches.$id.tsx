import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, EmptyState, ScoreBar, StatusBadge } from "@/components/shared/ui";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useApp } from "@/context/AppContext";
import { MATCHES } from "@/data/mock";
import {
  HeartHandshake,
  MapPin,
  ShieldCheck,
  CheckCircle2,
  Users,
  Package,
  type LucideIcon,
} from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/donor/matches/$id")({
  head: () => ({ meta: [{ title: "Match Details — Donate" }] }),
  component: MatchDetail,
});

function MatchDetail() {
  const { id } = Route.useParams();
  const { setDraft } = useApp();
  const navigate = useNavigate();
  const m = MATCHES.find((x) => x.id === id);

  if (!m) {
    return (
      <DashboardShell role="donor">
        <EmptyState
          title="Match not found"
          action={
            <Button asChild>
              <Link to="/donor/matches">Back to matches</Link>
            </Button>
          }
        />
      </DashboardShell>
    );
  }

  const select = () => {
    setDraft({ selectedMatch: m });
    toast.success(`Selected ${m.ngo.name}`);
    navigate({ to: "/donor/packaging" });
  };

  return (
    <DashboardShell role="donor">
      <PageHeader
        title={m.ngo.name}
        subtitle={m.ngo.mission}
        action={<Button onClick={select}>Donate to this NGO</Button>}
      />
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card className="p-6">
            <div className="flex items-center gap-3">
              <div className="grid h-14 w-14 place-items-center rounded-xl bg-primary/10 text-primary">
                <HeartHandshake className="h-7 w-7" />
              </div>
              <div>
                <div className="flex items-center gap-1">
                  <p className="text-lg font-semibold text-foreground">{m.ngo.name}</p>
                  {m.ngo.verified && <ShieldCheck className="h-5 w-5 text-primary" />}
                </div>
                <p className="flex items-center gap-1 text-sm text-muted-foreground">
                  <MapPin className="h-4 w-4" />
                  {m.ngo.city}, {m.ngo.state} · {m.ngo.distanceKm} km
                </p>
              </div>
            </div>
            <p className="mt-4 text-sm text-muted-foreground">{m.ngo.description}</p>
            <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
              <Stat
                icon={Users}
                label="Beneficiaries"
                value={m.ngo.beneficiaries.toLocaleString()}
              />
              <Stat
                icon={Package}
                label="Items received"
                value={m.ngo.itemsReceived.toLocaleString()}
              />
              <Stat icon={CheckCircle2} label="Active demands" value={m.ngo.activeDemands} />
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="font-semibold text-foreground">Why this NGO matched</h3>
            <ul className="mt-4 space-y-3">
              {m.reasons.map((r) => (
                <li key={r} className="flex items-start gap-3 text-sm text-foreground">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" /> {r}
                </li>
              ))}
            </ul>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="p-6 text-center">
            <p className="text-sm text-muted-foreground">Overall Match Score</p>
            <p className="mt-1 text-5xl font-extrabold text-primary">{m.overallScore}%</p>
            <div className="mt-3 flex justify-center">
              <StatusBadge status={m.urgency} />
            </div>
          </Card>
          <Card className="space-y-3 p-6">
            <h3 className="font-semibold text-foreground">Score breakdown</h3>
            <ScoreBar label="Item Type Match" value={m.breakdown.itemTypeMatch} />
            <ScoreBar label="Quantity Fit" value={m.breakdown.quantityFit} />
            <ScoreBar label="Geographic Proximity" value={m.breakdown.proximity} />
            <ScoreBar label="NGO Priority" value={m.breakdown.ngoPriority} />
          </Card>
          <Button className="w-full" onClick={select}>
            Donate to this NGO
          </Button>
        </div>
      </div>
    </DashboardShell>
  );
}

function Stat({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-lg bg-muted/40 p-3 text-center">
      <Icon className="mx-auto h-4 w-4 text-primary" />
      <p className="mt-1 text-lg font-bold text-foreground">{value}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, EmptyState } from "@/components/shared/ui";
import { DetectionOverlay, ConfidenceBadge } from "@/components/detection/DetectionOverlay";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useApp } from "@/context/AppContext";
import { Trash2, ArrowRight, ScanSearch, Camera } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/donor/detections")({
  head: () => ({ meta: [{ title: "Detection Results — Donate" }] }),
  component: Detections,
});

function Detections() {
  const { draft, setDraft } = useApp();
  const navigate = useNavigate();

  const remove = (id: string) => {
    setDraft({
      detections: draft.detections.filter((d) => d.id !== id),
      items: draft.items.filter((i) => i.id !== id),
    });
    toast("Detection removed");
  };

  if (!draft.detections.length) {
    return (
      <DashboardShell role="donor">
        <PageHeader title="Detection Results" />
        <EmptyState
          icon={ScanSearch}
          title="No detections yet"
          message="Scan or upload an image of your donation items to see AI-detected results."
          action={
            <Button asChild>
              <Link to="/donor/donate">
                <Camera className="mr-2 h-4 w-4" />
                Scan items
              </Link>
            </Button>
          }
        />
      </DashboardShell>
    );
  }

  return (
    <DashboardShell role="donor">
      <PageHeader
        title="Detection Results"
        subtitle={`AI detected ${draft.detections.length} item types in your image.`}
        action={
          <Button variant="outline" asChild>
            <Link to="/donor/donate">Re-analyze</Link>
          </Button>
        }
      />
      <div className="grid gap-6 lg:grid-cols-2">
        <DetectionOverlay image={draft.imageData} detections={draft.detections} />
        <div className="space-y-3">
          {draft.detections.map((d) => (
            <Card key={d.id} className="flex items-center justify-between gap-3 p-4">
              <div className="min-w-0">
                <p className="font-semibold text-foreground">{d.label}</p>
                <p className="text-sm text-muted-foreground">
                  {d.category} · Qty ~{d.quantity}
                </p>
                <div className="mt-2 flex items-center gap-2">
                  <ConfidenceBadge value={d.confidence} />
                  <div className="h-1.5 w-24 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full bg-primary"
                      style={{ width: `${d.confidence * 100}%` }}
                    />
                  </div>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Remove detection"
                onClick={() => remove(d.id)}
              >
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            </Card>
          ))}
          <Button className="w-full gap-2" onClick={() => navigate({ to: "/donor/review" })}>
            Continue to Review <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </DashboardShell>
  );
}

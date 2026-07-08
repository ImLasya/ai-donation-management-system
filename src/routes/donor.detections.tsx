import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, EmptyState } from "@/components/shared/ui";
import { DetectionOverlay, ConfidenceBadge } from "@/components/detection/DetectionOverlay";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { useApp } from "@/context/AppContext";
import { Trash2, ArrowRight, ScanSearch, Camera, Check, AlertTriangle, Info } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import type { Category } from "@/types";

export const Route = createFileRoute("/donor/detections")({
  head: () => ({ meta: [{ title: "Detection Results — Donate" }] }),
  component: Detections,
});

function Detections() {
  const { draft, setDraft } = useApp();
  const navigate = useNavigate();
  const [showIgnored, setShowIgnored] = useState(false);

  const confirmDetection = (id: string) => {
    const updatedDetections = draft.detections.map((d) =>
      d.id === id ? { ...d, confirmedByUser: true } : d
    );
    const targetDet = draft.detections.find((d) => d.id === id);
    if (!targetDet) return;

    // Check if it already exists in draft.items
    const existingIndex = draft.items.findIndex((item) => item.label === targetDet.label);
    let updatedItems = [...draft.items];
    if (existingIndex > -1) {
      updatedItems[existingIndex] = {
        ...updatedItems[existingIndex],
        quantity: updatedItems[existingIndex].quantity + 1,
      };
    } else {
      updatedItems.push({
        id: `grouped-review-${targetDet.id}-${Date.now()}`,
        label: targetDet.label,
        category: targetDet.category as Category,
        quantity: 1,
        confidence: targetDet.confidence,
        condition: "Not Assessed" as const,
      });
    }

    setDraft({
      detections: updatedDetections,
      items: updatedItems,
    });
    toast.success(`"${targetDet.label}" added as a donation item`);
  };

  const remove = (id: string) => {
    const targetDet = draft.detections.find((d) => d.id === id);
    if (!targetDet) return;

    let updatedItems = [...draft.items];
    const isApproved = targetDet.eligibilityStatus === "DONATABLE" || targetDet.confirmedByUser;
    
    if (isApproved) {
      const existingIndex = updatedItems.findIndex((item) => item.label === targetDet.label);
      if (existingIndex > -1) {
        if (updatedItems[existingIndex].quantity > 1) {
          updatedItems[existingIndex] = {
            ...updatedItems[existingIndex],
            quantity: updatedItems[existingIndex].quantity - 1,
          };
        } else {
          updatedItems = updatedItems.filter((_, idx) => idx !== existingIndex);
        }
      }
    }

    setDraft({
      detections: draft.detections.filter((d) => d.id !== id),
      items: updatedItems,
    });
    toast.info("Detection removed");
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

  // Filter detections based on toggle
  const overlayDetections = showIgnored
    ? draft.detections
    : draft.detections.filter((d) => d.eligibilityStatus !== "NON_DONATABLE");

  // A. Donation Items Detected (donatable or manually confirmed)
  const donationDetections = draft.detections.filter(
    (d) => d.eligibilityStatus === "DONATABLE" || d.confirmedByUser
  );

  // B. Ignored Non-Donation Objects (strictly non-donatable and not confirmed)
  const ignoredDetections = draft.detections.filter(
    (d) => d.eligibilityStatus === "NON_DONATABLE"
  );

  // C. Needs Review (review required and not confirmed)
  const reviewRequiredDetections = draft.detections.filter(
    (d) => d.eligibilityStatus === "REVIEW_REQUIRED" && !d.confirmedByUser
  );

  return (
    <DashboardShell role="donor">
      <PageHeader
        title="Detection Results"
        subtitle={`AI analyzed your image and filtered donation items.`}
        action={
          <Button variant="outline" asChild>
            <Link to="/donor/donate">Re-analyze</Link>
          </Button>
        }
      />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-4">
          <DetectionOverlay image={draft.imageData} detections={overlayDetections} />
          
          <div className="flex items-center space-x-2 rounded-lg border border-border p-3 bg-muted/20">
            <Switch
              id="show-ignored-toggle"
              checked={showIgnored}
              onCheckedChange={setShowIgnored}
            />
            <Label htmlFor="show-ignored-toggle" className="cursor-pointer text-sm font-medium text-foreground">
              Show ignored detections
            </Label>
          </div>
        </div>

        <div className="space-y-6">
          {/* Section A: Donation Items Detected */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              Donation Items Detected ({donationDetections.length})
            </h3>
            {donationDetections.length === 0 ? (
              <Card className="p-4 border-dashed border-border text-center text-sm text-muted-foreground">
                No eligible donation items detected yet.
              </Card>
            ) : (
              donationDetections.map((d) => (
                <Card key={d.id} className="flex items-center justify-between gap-3 p-4 border-primary/20 bg-primary/5">
                  <div className="min-w-0">
                    <p className="font-semibold text-foreground">{d.label}</p>
                    <p className="text-sm text-muted-foreground">
                      {d.category} · Confidence: {Math.round(d.confidence * 100)}%
                    </p>
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
              ))
            )}
          </div>

          {/* Section C: Needs Review */}
          {reviewRequiredDetections.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-amber-600 flex items-center gap-1.5">
                <AlertTriangle className="h-4 w-4 text-amber-500" />
                Needs Review ({reviewRequiredDetections.length})
              </h3>
              {reviewRequiredDetections.map((d) => (
                <Card key={d.id} className="flex items-center justify-between gap-3 p-4 border-amber-200 bg-amber-50/50">
                  <div className="min-w-0">
                    <p className="font-semibold text-foreground">{d.label}</p>
                    <div className="mt-1">
                      <ConfidenceBadge value={d.confidence} />
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      size="sm"
                      variant="outline"
                      className="text-amber-700 hover:text-amber-800 border-amber-200 bg-amber-50"
                      onClick={() => confirmDetection(d.id)}
                    >
                      <Check className="mr-1 h-3.5 w-3.5" /> Confirm
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Remove detection"
                      onClick={() => remove(d.id)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}

          {/* Section B: Ignored Non-Donation Objects */}
          {ignoredDetections.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Info className="h-4 w-4 text-muted-foreground" />
                Ignored Non-Donation Objects ({ignoredDetections.length})
              </h3>
              <div className="space-y-2 rounded-lg border border-border p-4 bg-muted/30">
                {ignoredDetections.map((d) => (
                  <div key={d.id} className="flex items-center justify-between text-xs text-muted-foreground border-b border-border/40 pb-2 last:border-0 last:pb-0">
                    <span className="font-medium text-foreground">{d.label}</span>
                    <span className="italic">{d.rejectionReason || "Not a donation item"}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <Button className="w-full gap-2 mt-4" onClick={() => navigate({ to: "/donor/review" })}>
            Continue to Review <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </DashboardShell>
  );
}

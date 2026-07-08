import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader } from "@/components/shared/ui";
import { CameraCapture } from "@/components/camera/CameraCapture";
import { Card } from "@/components/ui/card";
import { useApp } from "@/context/AppContext";
import { analyzeDonationImage } from "@/services/detectionService";
import { Loader2, CheckCircle2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import type { Category } from "@/types";

export const Route = createFileRoute("/donor/donate")({
  head: () => ({ meta: [{ title: "Donate Items — Donate" }] }),
  component: DonatePage,
});

const STAGES = [
  "Image preprocessing",
  "Object detection",
  "Item classification",
  "Catalog generation",
];

function DonatePage() {
  const { setDraft } = useApp();
  const navigate = useNavigate();
  const [analyzing, setAnalyzing] = useState(false);
  const [stage, setStage] = useState(0);

  useEffect(() => {
    if (!analyzing) return;
    const t = setInterval(() => setStage((s) => Math.min(s + 1, STAGES.length)), 550);
    return () => clearInterval(t);
  }, [analyzing]);

  const dataUrlToBlob = async (url: string): Promise<Blob> => {
    const res = await fetch(url);
    return await res.blob();
  };

  const handleCapture = async (dataUrl: string) => {
    setAnalyzing(true);
    setStage(0);
    setDraft({ imageData: dataUrl });

    try {
      setStage(1); // Preprocessing
      const blob = await dataUrlToBlob(dataUrl);

      setStage(2); // Object detection
      const res = await analyzeDonationImage(blob);

      setStage(3); // Catalog generation
      // Map bounding boxes from pixels to percentages for drawing overlay
      const detections = res.raw_detections.map((d) => ({
        id: d.id,
        label: d.label,
        category: d.donation_category as Category,
        quantity: 1,
        confidence: d.confidence,
        eligibilityStatus: d.eligibility_status,
        rejectionReason: d.rejection_reason,
        confirmedByUser: d.eligibility_status === "DONATABLE",
        bbox: {
          x: (d.bbox.x1 / res.image_width) * 100,
          y: (d.bbox.y1 / res.image_height) * 100,
          width: ((d.bbox.x2 - d.bbox.x1) / res.image_width) * 100,
          height: ((d.bbox.y2 - d.bbox.y1) / res.image_height) * 100,
        },
      }));

      // Grouped items default to "Not Assessed"
      const items = res.grouped_items.map((it, idx) => ({
        id: `grouped-${idx}-${Date.now()}`,
        label: it.item_name,
        category: it.category as Category,
        quantity: it.quantity,
        confidence: it.confidence,
        condition: "Not Assessed" as const,
      }));

      setDraft({ detections, items });
      toast.success("AI detection completed successfully!");
      navigate({ to: "/donor/detections" });
    } catch (err) {
      console.error("YOLO Inference Error:", err);
      toast.error(
        err instanceof Error
          ? err.message
          : "Object detection service is currently offline. Please try again.",
      );
      setAnalyzing(false);
    }
  };

  return (
    <DashboardShell role="donor">
      <PageHeader
        title="Scan Donation Items"
        subtitle="Photograph your items or upload an image — our AI will detect what you can donate."
      />
      {analyzing ? (
        <Card className="flex flex-col items-center px-6 py-16 text-center">
          <div className="relative">
            <Sparkles className="h-14 w-14 text-primary" />
            <span className="absolute -inset-2 animate-ping rounded-full bg-primary/20" />
          </div>
          <h2 className="mt-6 text-lg font-semibold text-foreground">Analyzing donation items…</h2>
          <p className="mt-1 text-sm text-muted-foreground">This usually takes a few seconds.</p>
          <div className="mt-8 w-full max-w-sm space-y-3 text-left">
            {STAGES.map((s, i) => (
              <div key={s} className="flex items-center gap-3">
                {i < stage ? (
                  <CheckCircle2 className="h-5 w-5 text-success" />
                ) : i === stage ? (
                  <Loader2 className="h-5 w-5 animate-spin text-primary" />
                ) : (
                  <div className="h-5 w-5 rounded-full border-2 border-muted" />
                )}
                <span className={i <= stage ? "text-foreground" : "text-muted-foreground"}>
                  {s}
                </span>
              </div>
            ))}
          </div>
        </Card>
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <CameraCapture onCapture={handleCapture} />
          </div>
          <Card className="p-5 space-y-4">
            <div className="flex items-center gap-2">
              <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
                <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636-.707.707M21 12h-1M4 12H3m1.636-6.364-.707-.707M6.343 17.657l-.707.707M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0z"/></svg>
              </div>
              <h3 className="font-semibold text-foreground">Tips for a good scan</h3>
            </div>
            <ul className="space-y-3">
              {[
                { icon: "☀️", tip: "Lay items out with good lighting" },
                { icon: "📷", tip: "Keep the camera steady and level" },
                { icon: "📦", tip: "Group similar items together" },
                { icon: "🧹", tip: "Avoid clutter and busy backgrounds" },
                { icon: "📐", tip: "Fill the frame — get close to items" },
              ].map(({ icon, tip }) => (
                <li key={tip} className="flex items-start gap-3 rounded-lg border border-border bg-muted/40 px-3 py-2.5 text-sm text-foreground">
                  <span className="text-base leading-none mt-0.5">{icon}</span>
                  <span>{tip}</span>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      )}
    </DashboardShell>
  );
}

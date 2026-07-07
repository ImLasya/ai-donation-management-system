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
      const detections = res.detections.map((d) => ({
        id: d.id,
        label: d.item_name,
        category: d.category as Category,
        quantity: 1,
        confidence: d.confidence,
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
          <Card className="p-5">
            <h3 className="font-semibold text-foreground">Tips for a good scan</h3>
            <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
              <li>• Lay items out with good lighting</li>
              <li>• Keep the camera steady and level</li>
              <li>• Group similar items together</li>
              <li>• Avoid clutter and busy backgrounds</li>
            </ul>
            <p className="mt-4 rounded-lg bg-muted p-3 text-xs text-muted-foreground">
              Detection runs on a mock AI model in demo mode. The flow is ready to connect to a
              YOLOv8 FastAPI endpoint via <code>POST /api/detection/analyze</code>.
            </p>
          </Card>
        </div>
      )}
    </DashboardShell>
  );
}

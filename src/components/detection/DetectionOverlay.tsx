import type { DetectionResult } from "@/types";

export function DetectionOverlay({
  image,
  detections,
}: {
  image?: string;
  detections: DetectionResult[];
}) {
  return (
    <div className="relative w-full overflow-hidden rounded-xl border border-border bg-foreground/90">
      {image ? (
        <img src={image} alt="Scanned donation items" className="w-full object-contain" />
      ) : (
        <div className="aspect-video w-full" />
      )}
      {detections.map((d, i) => (
        <div
          key={d.id}
          className="absolute rounded-md border-2 border-primary"
          style={{
            left: `${d.bbox.x}%`,
            top: `${d.bbox.y}%`,
            width: `${d.bbox.width}%`,
            height: `${d.bbox.height}%`,
          }}
        >
          <span className="absolute -top-6 left-0 whitespace-nowrap rounded bg-primary px-1.5 py-0.5 text-xs font-medium text-primary-foreground">
            {d.label} · {Math.round(d.confidence * 100)}%
          </span>
        </div>
      ))}
    </div>
  );
}

export function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const tone =
    pct >= 90
      ? "bg-success/10 text-success"
      : pct >= 75
        ? "bg-accent/20 text-accent-foreground"
        : "bg-destructive/10 text-destructive";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${tone}`}
    >
      {pct}% confident
    </span>
  );
}

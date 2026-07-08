import type { Category, BoundingBox } from "@/types";

export interface DetectionItemExtended {
  id: string;
  label: string;
  category: Category;
  quantity: number;
  confidence: number;
  bbox: BoundingBox;
  eligibilityStatus?: "DONATABLE" | "NON_DONATABLE" | "REVIEW_REQUIRED";
  confirmedByUser?: boolean;
}

export function DetectionOverlay({
  image,
  detections,
}: {
  image?: string;
  detections: DetectionItemExtended[];
}) {
  return (
    <div className="relative w-full overflow-hidden rounded-xl border border-border bg-foreground/90">
      {image ? (
        <img src={image} alt="Scanned donation items" className="w-full object-contain" />
      ) : (
        <div className="aspect-video w-full" />
      )}
      {detections.map((d) => {
        const isDonatable = d.eligibilityStatus === "DONATABLE" || d.confirmedByUser;
        const isReview = d.eligibilityStatus === "REVIEW_REQUIRED";

        let borderColor = "border-[#14b8a6]"; // primary teal
        let bgColor = "bg-[#14b8a6]";

        if (!isDonatable) {
          if (isReview) {
            borderColor = "border-[#f59e0b]"; // amber
            bgColor = "bg-[#f59e0b]";
          } else {
            borderColor = "border-[#9ca3af]"; // gray
            bgColor = "bg-[#9ca3af]";
          }
        }

        return (
          <div
            key={d.id}
            className={`absolute rounded-md border-2 ${borderColor}`}
            style={{
              left: `${d.bbox.x}%`,
              top: `${d.bbox.y}%`,
              width: `${d.bbox.width}%`,
              height: `${d.bbox.height}%`,
            }}
          >
            <span className={`absolute -top-6 left-0 whitespace-nowrap rounded px-1.5 py-0.5 text-xs font-medium text-white ${bgColor}`}>
              {d.label} · {Math.round(d.confidence * 100)}%
            </span>
          </div>
        );
      })}
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

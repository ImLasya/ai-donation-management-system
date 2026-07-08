export interface DetectionItem {
  id: string;
  class_id: number;
  label: string;
  normalized_label: string;
  confidence: number;
  bbox: {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
  };
  eligibility_status: "DONATABLE" | "NON_DONATABLE" | "REVIEW_REQUIRED";
  donation_category: string;
  rejection_reason: string | null;
}

export interface DetectionResponse {
  image_width: number;
  image_height: number;
  raw_detections: DetectionItem[];
  donatable_detections: DetectionItem[];
  rejected_detections: DetectionItem[];
  grouped_items: Array<{
    item_name: string;
    category: string;
    quantity: number;
    confidence: number;
  }>;
  detections?: DetectionItem[];
}

export async function analyzeDonationImage(file: File | Blob): Promise<DetectionResponse> {
  const form = new FormData();
  form.append("file", file, "donation.jpg");

  const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/detection/analyze`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Object detection service is currently unavailable.");
  }

  return (await res.json()) as DetectionResponse;
}

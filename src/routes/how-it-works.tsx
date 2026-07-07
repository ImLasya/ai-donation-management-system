import { createFileRoute, Link } from "@tanstack/react-router";
import { PublicLayout } from "@/components/portal/PublicLayout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Camera,
  ScanSearch,
  ListChecks,
  Sparkles,
  Package,
  CalendarClock,
  Truck,
  CheckCircle2,
} from "lucide-react";

export const Route = createFileRoute("/how-it-works")({
  head: () => ({
    meta: [
      { title: "How It Works — Donate" },
      {
        name: "description",
        content: "See how Donate turns a photo of your items into a matched, tracked donation.",
      },
    ],
  }),
  component: HowItWorks,
});

const FLOW = [
  {
    icon: Camera,
    title: "Camera Capture",
    text: "Photograph your donation items using your device camera or upload an image.",
  },
  {
    icon: ScanSearch,
    title: "AI Detection",
    text: "Our YOLOv8-ready pipeline detects item types, quantities, and confidence scores.",
  },
  {
    icon: ListChecks,
    title: "Review & Edit",
    text: "Adjust the detected catalog — edit names, quantities, and condition before submitting.",
  },
  {
    icon: Sparkles,
    title: "Intelligent Matching",
    text: "See NGOs ranked by item fit, quantity, proximity, and priority — with full transparency.",
  },
  {
    icon: Package,
    title: "Packaging Guidance",
    text: "Follow a category-specific checklist so items arrive in great condition.",
  },
  {
    icon: CalendarClock,
    title: "Schedule Pickup",
    text: "Pick a date and time slot; volunteers handle collection.",
  },
  {
    icon: Truck,
    title: "Track to Delivery",
    text: "Follow each stage from collection to acknowledgement in real time.",
  },
  {
    icon: CheckCircle2,
    title: "Acknowledgement",
    text: "Receive confirmation and see your measurable impact.",
  },
];

function HowItWorks() {
  return (
    <PublicLayout>
      <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:px-8">
        <h1 className="text-4xl font-bold text-foreground">How It Works</h1>
        <p className="mt-4 text-lg text-muted-foreground">
          A complete, transparent donation journey — powered by AI at every step.
        </p>
        <div className="mt-10 space-y-4">
          {FLOW.map((s, i) => (
            <Card key={s.title} className="flex items-start gap-4 p-5">
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
                <s.icon className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs font-semibold text-muted-foreground">STEP {i + 1}</p>
                <h3 className="font-semibold text-foreground">{s.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{s.text}</p>
              </div>
            </Card>
          ))}
        </div>
        <div className="mt-10 text-center">
          <Button asChild size="lg">
            <Link to="/login?redirect=/donor/donate">Try it now</Link>
          </Button>
        </div>
      </div>
    </PublicLayout>
  );
}

import { createFileRoute } from "@tanstack/react-router";
import { PublicLayout } from "@/components/portal/PublicLayout";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

export const Route = createFileRoute("/faq")({
  head: () => ({
    meta: [
      { title: "FAQ — Donate" },
      {
        name: "description",
        content: "Frequently asked questions about donating and matching with Donate.",
      },
    ],
  }),
  component: FAQ,
});

const FAQS = [
  [
    "How does the AI detect my items?",
    "You photograph items with your camera and our object-detection pipeline identifies item types, estimates quantities, and returns confidence scores. You can always edit the results before submitting.",
  ],
  [
    "Is my donation actually needed?",
    "Yes — matches are based on NGOs' live demand registries, so you only donate what an organisation has explicitly requested.",
  ],
  [
    "How is the match score calculated?",
    "We combine item type match, quantity fit, geographic proximity, and NGO priority into a transparent overall score, and we always explain why an NGO was matched.",
  ],
  [
    "Who picks up my donation?",
    "You schedule a convenient pickup slot and NGO volunteers or logistics partners handle collection.",
  ],
  [
    "Can NGOs register?",
    "Absolutely. NGOs register, get verified by admins, and maintain a live demand registry to receive matched donations.",
  ],
  ["Is Donate free?", "Yes, the platform is free for donors and partner NGOs."],
];

function FAQ() {
  return (
    <PublicLayout>
      <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6 lg:px-8">
        <h1 className="text-4xl font-bold text-foreground">Frequently Asked Questions</h1>
        <Accordion type="single" collapsible className="mt-8">
          {FAQS.map(([q, a], i) => (
            <AccordionItem key={i} value={`item-${i}`}>
              <AccordionTrigger className="text-left">{q}</AccordionTrigger>
              <AccordionContent className="text-muted-foreground">{a}</AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </PublicLayout>
  );
}

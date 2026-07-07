import { createFileRoute } from "@tanstack/react-router";
import { PublicLayout } from "@/components/portal/PublicLayout";
import { Card } from "@/components/ui/card";
import { Target, Eye, Users } from "lucide-react";

export const Route = createFileRoute("/about")({
  head: () => ({
    meta: [
      { title: "About — Donate" },
      {
        name: "description",
        content:
          "Donate connects donors and NGOs through AI-powered resource matching for efficient, transparent giving.",
      },
    ],
  }),
  component: About,
});

function About() {
  return (
    <PublicLayout>
      <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
        <h1 className="text-4xl font-bold text-foreground">About Donate</h1>
        <p className="mt-4 text-lg text-muted-foreground">
          Donation processes for NGOs are often manual and inefficient. Donors struggle to know what
          items are actually needed, while NGOs cannot communicate real-time needs. Donate bridges
          this gap with an AI-powered, two-sided platform for intelligent resource matching and
          distribution.
        </p>
        <div className="mt-10 grid gap-6 sm:grid-cols-3">
          {[
            {
              icon: Target,
              title: "Our Mission",
              text: "Eliminate mismatched donations by matching every item to a genuine, verified need.",
            },
            {
              icon: Eye,
              title: "Our Vision",
              text: "A world where giving is effortless, transparent, and reaches the people who need it most.",
            },
            {
              icon: Users,
              title: "Who We Serve",
              text: "Individual donors, grassroots NGOs, and administrators coordinating impact at scale.",
            },
          ].map((c) => (
            <Card key={c.title} className="p-6">
              <div className="grid h-11 w-11 place-items-center rounded-xl bg-primary/10 text-primary">
                <c.icon className="h-5 w-5" />
              </div>
              <h3 className="mt-4 font-semibold text-foreground">{c.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{c.text}</p>
            </Card>
          ))}
        </div>
      </div>
    </PublicLayout>
  );
}

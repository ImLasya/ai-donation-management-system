import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { PublicLayout } from "@/components/portal/PublicLayout";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { StatusBadge } from "@/components/shared/ui";
import { NGOS } from "@/data/mock";
import { HeartHandshake, MapPin, ShieldCheck, Search } from "lucide-react";

export const Route = createFileRoute("/find-ngos")({
  head: () => ({
    meta: [
      { title: "Find NGOs — Donate" },
      {
        name: "description",
        content: "Browse verified NGOs and see their active donation demands.",
      },
    ],
  }),
  component: FindNGOs,
});

function FindNGOs() {
  const [q, setQ] = useState("");
  const filtered = NGOS.filter(
    (n) =>
      n.name.toLowerCase().includes(q.toLowerCase()) ||
      n.city.toLowerCase().includes(q.toLowerCase()),
  );
  return (
    <PublicLayout>
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <h1 className="text-4xl font-bold text-foreground">Find NGOs</h1>
        <p className="mt-3 text-muted-foreground">
          Discover verified organisations and the items they need right now.
        </p>
        <div className="relative mt-6 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search by name or city…"
            className="pl-9"
          />
        </div>
        <div className="mt-8 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((n) => (
            <Card key={n.id} className="p-6">
              <div className="flex items-center gap-3">
                <div className="grid h-11 w-11 place-items-center rounded-xl bg-primary/10 text-primary">
                  <HeartHandshake className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-1">
                    <p className="truncate font-semibold text-foreground">{n.name}</p>
                    {n.verified && <ShieldCheck className="h-4 w-4 shrink-0 text-primary" />}
                  </div>
                  <p className="flex items-center gap-1 text-xs text-muted-foreground">
                    <MapPin className="h-3 w-3" />
                    {n.city}, {n.state}
                  </p>
                </div>
              </div>
              <p className="mt-3 line-clamp-2 text-sm text-muted-foreground">{n.description}</p>
              <div className="mt-4 flex flex-wrap gap-1">
                {n.categories.slice(0, 4).map((c) => (
                  <span
                    key={c}
                    className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground"
                  >
                    {c}
                  </span>
                ))}
              </div>
              <div className="mt-4 flex items-center justify-between">
                <StatusBadge status={n.priority} />
                <span className="text-xs text-muted-foreground">
                  {n.activeDemands} active demands
                </span>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </PublicLayout>
  );
}

import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Camera,
  Sparkles,
  Truck,
  ShieldCheck,
  ArrowRight,
  MapPin,
  Star,
  Package,
  HeartHandshake,
  CheckCircle2,
} from "lucide-react";
import * as Icons from "lucide-react";
import { PublicLayout } from "@/components/portal/PublicLayout";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/ui";
import { CATEGORIES, NGOS } from "@/data/mock";
import hero from "@/assets/hero.jpg";

export const Route = createFileRoute("/")({ component: Home });

const STEPS = [
  {
    icon: Camera,
    title: "Scan Your Items",
    desc: "Use your camera to photograph what you want to donate.",
  },
  {
    icon: Sparkles,
    title: "AI Detects & Matches",
    desc: "Our AI identifies items and finds NGOs that need them.",
  },
  {
    icon: Package,
    title: "Pack & Schedule",
    desc: "Get packaging guidance and book a convenient pickup.",
  },
  {
    icon: Truck,
    title: "Track to Delivery",
    desc: "Follow your donation from collection to acknowledgement.",
  },
];

const STATS = [
  { value: "48,200+", label: "Items Donated" },
  { value: "1,240", label: "Active NGOs" },
  { value: "92%", label: "Match Success Rate" },
  { value: "310K", label: "People Impacted" },
];

const TESTIMONIALS = [
  {
    name: "Meera K.",
    role: "Donor",
    quote:
      "I finally know my donations reach people who actually need them. The AI matching is brilliant.",
  },
  {
    name: "Hope Foundation",
    role: "NGO Partner",
    quote:
      "The demand registry means we get exactly what we ask for. No more mismatched donations.",
  },
  {
    name: "Rahul S.",
    role: "Donor",
    quote: "Scanning items with my phone and booking a pickup took under two minutes.",
  },
];

function Home() {
  return (
    <PublicLayout>
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 -z-10 bg-gradient-to-br from-primary/5 via-background to-secondary/5" />
        <div className="mx-auto grid max-w-7xl items-center gap-10 px-4 py-16 sm:px-6 lg:grid-cols-2 lg:px-8 lg:py-24">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1 text-sm font-medium text-primary">
              <Sparkles className="h-4 w-4" /> AI-Powered Donation Matching
            </span>
            <h1 className="mt-5 text-4xl font-extrabold tracking-tight text-foreground sm:text-5xl">
              Give smarter. Match donations to the NGOs that need them most.
            </h1>
            <p className="mt-5 text-lg text-muted-foreground">
              Scan your items, let AI detect and match them to verified NGO demands, then schedule
              pickup and track every donation to delivery — transparently.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg" className="gap-2">
                <Link to="/login?redirect=/donor/donate">
                  Donate Items <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link to="/register">Register NGO</Link>
              </Button>
            </div>
            <div className="mt-6 flex items-center gap-4 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <ShieldCheck className="h-4 w-4 text-primary" /> Verified NGOs
              </span>
              <span className="flex items-center gap-1">
                <CheckCircle2 className="h-4 w-4 text-primary" /> Transparent matching
              </span>
            </div>
          </div>
          <div className="relative">
            <img
              src={hero}
              alt="People donating boxes of books, clothes and food to volunteers"
              width={1280}
              height={960}
              className="rounded-2xl border border-border shadow-xl"
            />
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="border-y border-border bg-card">
        <div className="mx-auto grid max-w-7xl grid-cols-2 gap-6 px-4 py-10 sm:px-6 lg:grid-cols-4 lg:px-8">
          {STATS.map((s) => (
            <div key={s.label} className="text-center">
              <p className="text-3xl font-extrabold text-primary">{s.value}</p>
              <p className="mt-1 text-sm text-muted-foreground">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold text-foreground">How It Works</h2>
          <p className="mt-3 text-muted-foreground">
            From your camera to a family in need — in four simple steps.
          </p>
        </div>
        <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s, i) => (
            <Card key={s.title} className="p-6">
              <div className="grid h-11 w-11 place-items-center rounded-xl bg-primary/10 text-primary">
                <s.icon className="h-5 w-5" />
              </div>
              <p className="mt-4 text-xs font-semibold text-muted-foreground">STEP {i + 1}</p>
              <h3 className="mt-1 text-lg font-semibold text-foreground">{s.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{s.desc}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* Categories */}
      <section className="border-y border-border bg-card">
        <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
          <h2 className="text-center text-3xl font-bold text-foreground">
            Supported Donation Categories
          </h2>
          <div className="mt-10 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            {CATEGORIES.map((c) => {
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              const Icon = (Icons as any)[c.icon] ?? Package;
              return (
                <Card
                  key={c.name}
                  className="flex flex-col items-center gap-2 p-4 text-center transition-shadow hover:shadow-md"
                >
                  <div className="grid h-10 w-10 place-items-center rounded-lg bg-primary/10 text-primary">
                    <Icon className="h-5 w-5" />
                  </div>
                  <span className="text-sm font-medium text-foreground">{c.name}</span>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      {/* Featured NGOs */}
      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="flex items-end justify-between">
          <h2 className="text-3xl font-bold text-foreground">Featured NGOs</h2>
          <Button asChild variant="ghost" className="gap-1">
            <Link to="/find-ngos">
              View all <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>
        <div className="mt-8 grid gap-6 md:grid-cols-3">
          {NGOS.slice(0, 3).map((n) => (
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
              <p className="mt-3 line-clamp-2 text-sm text-muted-foreground">{n.mission}</p>
              <div className="mt-4 flex items-center justify-between">
                <StatusBadge status={n.priority} />
                <span className="text-xs text-muted-foreground">
                  {n.beneficiaries.toLocaleString()} helped
                </span>
              </div>
            </Card>
          ))}
        </div>
      </section>

      {/* Testimonials */}
      <section className="border-t border-border bg-card">
        <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
          <h2 className="text-center text-3xl font-bold text-foreground">
            Loved by donors and NGOs
          </h2>
          <div className="mt-10 grid gap-6 md:grid-cols-3">
            {TESTIMONIALS.map((t) => (
              <Card key={t.name} className="p-6">
                <div className="flex gap-1 text-accent">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Star key={i} className="h-4 w-4 fill-current" />
                  ))}
                </div>
                <p className="mt-3 text-sm text-foreground">"{t.quote}"</p>
                <p className="mt-4 text-sm font-semibold text-foreground">{t.name}</p>
                <p className="text-xs text-muted-foreground">{t.role}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="rounded-3xl bg-gradient-to-br from-primary to-primary-dark px-8 py-14 text-center text-primary-foreground">
          <h2 className="text-3xl font-bold">Ready to make your donation count?</h2>
          <p className="mx-auto mt-3 max-w-xl text-primary-foreground/80">
            Join thousands of donors using AI to give exactly what NGOs need.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Button asChild size="lg" variant="secondary">
              <Link to="/login?redirect=/donor/donate">Start Donating</Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="border-primary-foreground/30 bg-transparent text-primary-foreground hover:bg-primary-foreground/10"
            >
              <Link to="/how-it-works">Learn more</Link>
            </Button>
          </div>
        </div>
      </section>
    </PublicLayout>
  );
}

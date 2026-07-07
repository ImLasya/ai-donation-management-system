import { createFileRoute, Link } from "@tanstack/react-router";
import { HeartHandshake, ArrowRight, HandHeart, Building2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export const Route = createFileRoute("/register/")({
  head: () => ({
    meta: [
      { title: "Create an account — Donate" },
      {
        name: "description",
        content: "Choose how you’d like to join Donate as a donor or NGO partner.",
      },
    ],
  }),
  component: RegisterChoice,
});

function RegisterChoice() {
  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto flex min-h-screen max-w-6xl flex-col justify-center px-4 py-16 sm:px-6 lg:px-8">
        <div className="mb-10 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="grid h-9 w-9 place-items-center rounded-lg bg-primary text-primary-foreground">
              <HeartHandshake className="h-5 w-5" />
            </div>
            <span className="text-lg font-bold text-foreground">Donate</span>
          </Link>
          <Link to="/login" className="text-sm font-medium text-primary hover:underline">
            Sign in
          </Link>
        </div>
        <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="rounded-3xl bg-gradient-to-br from-primary to-primary-dark p-8 text-primary-foreground">
            <p className="text-sm font-semibold uppercase tracking-[0.25em] text-primary-foreground/70">
              Join Donate
            </p>
            <h1 className="mt-4 text-3xl font-bold">
              Create a secure account that matches your role.
            </h1>
            <p className="mt-4 text-sm text-primary-foreground/80">
              Choose whether you want to donate items or represent an NGO and coordinate impact at
              scale.
            </p>
          </div>
          <div className="grid gap-4">
            <Card className="p-6">
              <div className="flex items-start gap-3">
                <div className="grid h-11 w-11 place-items-center rounded-xl bg-primary/10 text-primary">
                  <HandHeart className="h-5 w-5" />
                </div>
                <div className="flex-1">
                  <h2 className="text-xl font-semibold text-foreground">I want to donate</h2>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Create a donor account to scan items, match them with NGOs, and track your
                    impact.
                  </p>
                  <Button asChild className="mt-4 gap-2">
                    <Link to="/register/donor">
                      Create donor account <ArrowRight className="h-4 w-4" />
                    </Link>
                  </Button>
                </div>
              </div>
            </Card>
            <Card className="p-6">
              <div className="flex items-start gap-3">
                <div className="grid h-11 w-11 place-items-center rounded-xl bg-primary/10 text-primary">
                  <Building2 className="h-5 w-5" />
                </div>
                <div className="flex-1">
                  <h2 className="text-xl font-semibold text-foreground">I represent an NGO</h2>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Register your organization to publish demands, receive donations, and streamline
                    delivery.
                  </p>
                  <Button asChild variant="outline" className="mt-4 gap-2">
                    <Link to="/register/ngo">
                      Create NGO account <ArrowRight className="h-4 w-4" />
                    </Link>
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

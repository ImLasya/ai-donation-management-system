import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMemo, useState, useEffect } from "react";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader } from "@/components/shared/ui";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Progress } from "@/components/ui/progress";
import { useApp } from "@/context/AppContext";
import { PACKAGING_TIPS } from "@/data/mock";
import { Printer, ArrowRight } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/donor/packaging")({
  head: () => ({ meta: [{ title: "Packaging Checklist — Donate" }] }),
  component: Packaging,
});

function Packaging() {
  const { draft, setDraft } = useApp();
  const navigate = useNavigate();
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [authorized, setAuthorized] = useState(false);

  useEffect(() => {
    const checkStatus = async () => {
      const donationId = draft.donationId;
      if (!donationId) {
        toast.error("No active donation found. Please submit your items first.");
        navigate({ to: "/donor/donate" });
        return;
      }

      try {
        const token = localStorage.getItem("da_token");
        const res = await fetch(
          `${import.meta.env.VITE_API_BASE_URL}/api/donations/${donationId}/track`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          },
        );
        if (res.ok) {
          const data = await res.json();
          if (data.status === "NGO_ACCEPTED" || data.status === "PACKAGING_IN_PROGRESS") {
            setAuthorized(true);
            setItems(data.items);

            if (data.status === "NGO_ACCEPTED") {
              // Notify backend that packaging is in progress
              fetch(
                `${import.meta.env.VITE_API_BASE_URL}/api/donations/${donationId}/start-packaging`,
                {
                  method: "POST",
                  headers: {
                    Authorization: `Bearer ${token}`,
                  },
                },
              ).catch((e) =>
                console.error("Failed to transition status to packaging in progress:", e),
              );
            }
          } else {
            toast.error(
              `Packaging is only accessible after NGO acceptance. Status: ${data.status}`,
            );
            navigate({ to: "/donor/track/$id", params: { id: String(donationId) } });
          }
        } else {
          toast.error("Failed to load donation details.");
          navigate({ to: "/donor/donations" });
        }
      } catch (err) {
        console.error(err);
        navigate({ to: "/donor/donations" });
      } finally {
        setLoading(false);
      }
    };
    checkStatus();
  }, [draft.donationId]);

  const categories = useMemo(() => {
    const cats = [...new Set(items.map((i) => i.category))];
    return cats.length ? cats : (["Books", "Clothing"] as const);
  }, [items]);

  const allTips = useMemo(
    () =>
      categories.flatMap((c) =>
        (PACKAGING_TIPS[c] ?? PACKAGING_TIPS.default).map((t) => `${c}: ${t}`),
      ),
    [categories],
  );

  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const done = allTips.filter((t) => checked[t]).length;
  const pct = allTips.length ? Math.round((done / allTips.length) * 100) : 0;

  if (loading) {
    return (
      <DashboardShell role="donor">
        <div className="flex h-64 items-center justify-center">
          <p className="text-muted-foreground font-medium">Verifying packaging authorization...</p>
        </div>
      </DashboardShell>
    );
  }

  if (!authorized) return null;

  return (
    <DashboardShell role="donor">
      <PageHeader
        title="Packaging Checklist"
        subtitle="Category-specific guidance so items arrive in great condition."
        action={
          <Button variant="outline" className="gap-2" onClick={() => window.print()}>
            <Printer className="h-4 w-4" /> Print
          </Button>
        }
      />
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card className="p-6">
            <div className="mb-4">
              <div className="mb-1 flex justify-between text-sm">
                <span className="text-muted-foreground">Progress</span>
                <span className="font-semibold text-foreground">{pct}%</span>
              </div>
              <Progress value={pct} />
            </div>
            <div className="space-y-6">
              {categories.map((c) => (
                <div key={c}>
                  <h3 className="mb-2 font-semibold text-foreground">{c}</h3>
                  <div className="space-y-2">
                    {(PACKAGING_TIPS[c] ?? PACKAGING_TIPS.default).map((t) => {
                      const key = `${c}: ${t}`;
                      return (
                        <label
                          key={key}
                          className="flex cursor-pointer items-center gap-3 rounded-lg border border-border p-3 text-sm hover:bg-muted/40"
                        >
                          <Checkbox
                            checked={!!checked[key]}
                            onCheckedChange={(v) => setChecked((p) => ({ ...p, [key]: !!v }))}
                          />
                          <span
                            className={
                              checked[key]
                                ? "text-muted-foreground line-through"
                                : "text-foreground"
                            }
                          >
                            {t}
                          </span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
        <div>
          <Card className="sticky top-24 p-6">
            <h3 className="font-semibold text-foreground">Ready to ship?</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Complete the checklist, then mark packaging done to schedule your pickup.
            </p>
            <Button
              className="mt-4 w-full gap-2"
              disabled={pct < 100}
              onClick={async () => {
                const donationId = draft.donationId;
                try {
                  const token = localStorage.getItem("da_token");
                  const res = await fetch(
                    `${import.meta.env.VITE_API_BASE_URL}/api/donations/${donationId}/package`,
                    {
                      method: "POST",
                      headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${token}`,
                      },
                      body: JSON.stringify({
                        package_count: 1,
                        packaging_notes:
                          "Items securely wrapped and packaged following suggestions.",
                      }),
                    },
                  );

                  if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    throw new Error(errData.detail || "Failed to update packaging status.");
                  }

                  setDraft({ packagingDone: true });
                  toast.success("Packaging marked complete!");
                  navigate({ to: "/donor/schedule" });
                } catch (err) {
                  console.error(err);
                  toast.error(err instanceof Error ? err.message : "Failed to complete packaging.");
                }
              }}
            >
              Mark Packaging Complete <ArrowRight className="h-4 w-4" />
            </Button>
            {pct < 100 && (
              <p className="mt-2 text-center text-xs text-muted-foreground">
                Complete all items to continue
              </p>
            )}
          </Card>
        </div>
      </div>
    </DashboardShell>
  );
}

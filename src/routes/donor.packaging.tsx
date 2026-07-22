import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMemo, useState, useEffect } from "react";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader } from "@/components/shared/ui";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useApp } from "@/context/AppContext";
import { Printer, ArrowRight } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/donor/packaging")({
  head: () => ({ meta: [{ title: "Packaging Checklist — Donate" }] }),
  component: Packaging,
});

function Packaging() {
  const { draft, setDraft } = useApp();
  const navigate = useNavigate();
  const [checklist, setChecklist] = useState<Record<string, string[]>>({});
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [packageCount, setPackageCount] = useState<number>(1);
  const [packagingNotes, setPackagingNotes] = useState<string>(
    "Items securely wrapped and packaged following suggestions."
  );
  const [loading, setLoading] = useState(true);
  const [authorized, setAuthorized] = useState(false);

  useEffect(() => {
    const fetchChecklistData = async () => {
      const donationId = draft.donationId;
      if (!donationId) {
        toast.error("No active donation found. Please submit your items first.");
        navigate({ to: "/donor/donate" });
        return;
      }

      try {
        const token = localStorage.getItem("da_token");
        
        // 1. First verify status and start packaging if needed
        const trackRes = await fetch(
          `${import.meta.env.VITE_API_BASE_URL}/api/donations/${donationId}/track`,
          { headers: { Authorization: `Bearer ${token}` } }
        );

        if (trackRes.ok) {
          const trackData = await trackRes.json();
          if (trackData.status === "NGO_ACCEPTED" || trackData.status === "PACKAGING_IN_PROGRESS") {
            setAuthorized(true);

            if (trackData.status === "NGO_ACCEPTED") {
              await fetch(
                `${import.meta.env.VITE_API_BASE_URL}/api/donations/${donationId}/start-packaging`,
                {
                  method: "POST",
                  headers: { Authorization: `Bearer ${token}` },
                }
              ).catch((e) =>
                console.error("Failed to transition status to packaging in progress:", e)
              );
            }
            
            // 2. Fetch the actual checklist tips and persistence state
            const listRes = await fetch(
              `${import.meta.env.VITE_API_BASE_URL}/api/donations/${donationId}/packaging-checklist`,
              { headers: { Authorization: `Bearer ${token}` } }
            );

            if (listRes.ok) {
              const listData = await listRes.json();
              setChecklist(listData.checklist || {});
              setPackageCount(listData.packageCount || 1);
              if (listData.packagingNotes) {
                setPackagingNotes(listData.packagingNotes);
              }
              
              // Restore checkboxes state
              const restoredChecked: Record<string, boolean> = {};
              if (listData.completedItems) {
                listData.completedItems.forEach((key: string) => {
                  restoredChecked[key] = true;
                });
              }
              setChecked(restoredChecked);
            }
          } else {
            toast.error(`Packaging is only accessible after NGO acceptance. Status: ${trackData.status}`);
            navigate({ to: "/donor/track/$id", params: { id: String(donationId) } });
          }
        } else {
          toast.error("Failed to load donation details.");
          navigate({ to: "/donor/donations" });
        }
      } catch (err) {
        console.error("Error loading checklist:", err);
        navigate({ to: "/donor/donations" });
      } finally {
        setLoading(false);
      }
    };
    fetchChecklistData();
  }, [draft.donationId]);

  // Flatten tips to calculate completion percentage
  const allTips = useMemo(() => {
    return Object.entries(checklist).flatMap(([category, tips]) =>
      tips.map((tip) => `${category}: ${tip}`)
    );
  }, [checklist]);

  const doneCount = allTips.filter((t) => checked[t]).length;
  const pct = allTips.length ? Math.round((doneCount / allTips.length) * 100) : 0;

  if (loading) {
    return (
      <DashboardShell role="donor">
        <div className="flex h-64 items-center justify-center">
          <p className="text-muted-foreground font-medium">Loading category checklist...</p>
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
            <Printer className="h-4 w-4" /> Print Checklist
          </Button>
        }
      />
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card className="p-6">
            <div className="mb-4">
              <div className="mb-1 flex justify-between text-sm">
                <span className="text-muted-foreground font-medium">Progress</span>
                <span className="font-semibold text-primary">{pct}% Completed</span>
              </div>
              <Progress value={pct} />
            </div>
            
            <div className="space-y-6 mt-4">
              {Object.entries(checklist).map(([category, tips]) => (
                <div key={category} className="space-y-3">
                  <h3 className="text-base font-bold text-foreground border-l-4 border-primary pl-2">{category} Packaging Checklist</h3>
                  <div className="space-y-2">
                    {tips.map((tip) => {
                      const key = `${category}: ${tip}`;
                      return (
                        <label
                          key={key}
                          className="flex cursor-pointer items-center gap-3 rounded-lg border border-border p-3 text-sm hover:bg-muted/40 transition-colors"
                        >
                          <Checkbox
                            checked={!!checked[key]}
                            onCheckedChange={(v) => setChecked((p) => ({ ...p, [key]: !!v }))}
                          />
                          <span className={checked[key] ? "text-muted-foreground line-through font-medium" : "text-foreground font-medium"}>
                            {tip}
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
          <Card className="sticky top-24 p-6 space-y-4">
            <div>
              <h3 className="font-semibold text-foreground text-base">Package Summary</h3>
              <p className="text-xs text-muted-foreground mt-1">
                Enter details regarding how the items are packed for courier pick-up.
              </p>
            </div>
            
            <div className="space-y-1">
              <label htmlFor="packageCount" className="text-xs font-bold text-muted-foreground uppercase">Number of Packages</label>
              <Input
                id="packageCount"
                type="number"
                min={1}
                value={packageCount}
                onChange={(e) => setPackageCount(Math.max(1, parseInt(e.target.value) || 1))}
                className="w-full"
              />
            </div>
            
            <div className="space-y-1">
              <label htmlFor="packagingNotes" className="text-xs font-bold text-muted-foreground uppercase">Courier Pickup Instructions / Notes</label>
              <Textarea
                id="packagingNotes"
                placeholder="E.g. Fragile items inside box 2, call upon arrival"
                value={packagingNotes}
                onChange={(e) => setPackagingNotes(e.target.value)}
                className="min-h-[80px]"
              />
            </div>

            <Button
              className="w-full gap-2 bg-teal-600 hover:bg-teal-700"
              disabled={pct < 100}
              onClick={async () => {
                const donationId = draft.donationId;
                try {
                  const token = localStorage.getItem("da_token");
                  
                  // Serialize only the checked checkbox keys
                  const completedItems = Object.keys(checked).filter((k) => checked[k]);
                  
                  const res = await fetch(
                    `${import.meta.env.VITE_API_BASE_URL}/api/donations/${donationId}/package`,
                    {
                      method: "POST",
                      headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${token}`,
                      },
                      body: JSON.stringify({
                        package_count: packageCount,
                        packaging_notes: packagingNotes,
                        completed_items: completedItems
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
              <p className="text-center text-xs text-muted-foreground italic font-medium">
                Please check off all packaging suggestions above to continue.
              </p>
            )}
          </Card>
        </div>
      </div>
    </DashboardShell>
  );
}

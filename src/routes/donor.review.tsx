import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, EmptyState } from "@/components/shared/ui";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useApp } from "@/context/AppContext";
import { CATEGORIES } from "@/data/mock";
import type { Category, Condition, DonationItem } from "@/types";
import { Minus, Plus, Trash2, PlusCircle, ArrowRight, ListChecks } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/donor/review")({
  head: () => ({ meta: [{ title: "Review Items — Donate" }] }),
  component: Review,
});

const CONDITIONS: Condition[] = [
  "Not Assessed",
  "New",
  "Like New",
  "Good",
  "Fair",
  "Needs Repair",
  "Poor",
];

function Review() {
  const { draft, setDraft } = useApp();
  const navigate = useNavigate();
  const items = draft.items;

  const patch = (id: string, p: Partial<DonationItem>) =>
    setDraft({ items: items.map((it) => (it.id === id ? { ...it, ...p } : it)) });
  const remove = (id: string) => setDraft({ items: items.filter((it) => it.id !== id) });
  const addItem = () =>
    setDraft({
      items: [
        ...items,
        {
          id: `new_${Date.now()}`,
          label: "New item",
          category: "Other",
          quantity: 1,
          condition: "Not Assessed",
        },
      ],
    });

  const totalQty = items.reduce((s, i) => s + i.quantity, 0);

  if (!items.length) {
    return (
      <DashboardShell role="donor">
        <PageHeader title="Review Donation Items" />
        <EmptyState
          icon={ListChecks}
          title="No items to review"
          message="Scan items first, then edit the detected catalog here."
          action={
            <Button asChild>
              <Link to="/donor/donate">Scan items</Link>
            </Button>
          }
        />
      </DashboardShell>
    );
  }

  return (
    <DashboardShell role="donor">
      <PageHeader
        title="Review Donation Items"
        subtitle="Edit the AI-detected catalog before finding matched NGOs."
        action={
          <Button variant="outline" onClick={addItem} className="gap-2">
            <PlusCircle className="h-4 w-4" /> Add item
          </Button>
        }
      />
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          {items.map((it) => (
            <Card key={it.id} className="p-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <Label>Item name</Label>
                  <Input
                    className="mt-1"
                    value={it.label}
                    onChange={(e) => patch(it.id, { label: e.target.value })}
                  />
                </div>
                <div>
                  <Label>Category</Label>
                  <Select
                    value={it.category}
                    onValueChange={(v) => patch(it.id, { category: v as Category })}
                  >
                    <SelectTrigger className="mt-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CATEGORIES.map((c) => (
                        <SelectItem key={c.name} value={c.name}>
                          {c.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Quantity</Label>
                  <div className="mt-1 flex items-center gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      aria-label="Decrease"
                      onClick={() => patch(it.id, { quantity: Math.max(1, it.quantity - 1) })}
                    >
                      <Minus className="h-4 w-4" />
                    </Button>
                    <Input
                      type="number"
                      min={1}
                      className="w-20 text-center"
                      value={it.quantity}
                      onChange={(e) =>
                        patch(it.id, { quantity: Math.max(1, Number(e.target.value) || 1) })
                      }
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      aria-label="Increase"
                      onClick={() => patch(it.id, { quantity: it.quantity + 1 })}
                    >
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <div>
                  <Label>Condition</Label>
                  <Select
                    value={it.condition}
                    onValueChange={(v) => patch(it.id, { condition: v as Condition })}
                  >
                    <SelectTrigger className="mt-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CONDITIONS.map((c) => (
                        <SelectItem key={c} value={c}>
                          {c}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="sm:col-span-2">
                  <Label>Notes (optional)</Label>
                  <Input
                    className="mt-1"
                    placeholder="e.g. Grade 6-8 syllabus"
                    value={it.notes ?? ""}
                    onChange={(e) => patch(it.id, { notes: e.target.value })}
                  />
                </div>
              </div>
              <div className="mt-3 flex items-center justify-between">
                {it.confidence != null ? (
                  <span className="text-xs text-muted-foreground">
                    Detected at {Math.round(it.confidence * 100)}% confidence
                  </span>
                ) : (
                  <span className="text-xs text-muted-foreground">Manually added</span>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-2 text-destructive"
                  onClick={() => remove(it.id)}
                >
                  <Trash2 className="h-4 w-4" /> Remove
                </Button>
              </div>
            </Card>
          ))}
        </div>
        <div>
          <Card className="sticky top-24 p-5">
            <h3 className="font-semibold text-foreground">Donation Summary</h3>
            <dl className="mt-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Unique items</dt>
                <dd className="font-medium text-foreground">{items.length}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Total quantity</dt>
                <dd className="font-medium text-foreground">{totalQty}</dd>
              </div>
            </dl>
            <div className="mt-4 border-t border-border pt-4">
              <p className="mb-2 text-xs font-medium text-muted-foreground">Categories</p>
              <div className="flex flex-wrap gap-1">
                {[...new Set(items.map((i) => i.category))].map((c) => (
                  <span
                    key={c}
                    className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground"
                  >
                    {c}
                  </span>
                ))}
              </div>
            </div>
            <Button
              className="mt-5 w-full gap-2"
              onClick={async () => {
                try {
                  const token = localStorage.getItem("da_token");
                  if (!token) {
                    toast.error("Please login to submit donation.");
                    return;
                  }

                  const payload = {
                    items: items.map((it) => ({
                      item_name: it.label,
                      category: it.category,
                      quantity: it.quantity,
                      condition: it.condition,
                      confidence_score: it.confidence ?? null,
                      source: it.confidence ? "AI" : "MANUAL",
                      is_confirmed: true,
                    })),
                  };

                  const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/donations`, {
                    method: "POST",
                    headers: {
                      "Content-Type": "application/json",
                      Authorization: `Bearer ${token}`,
                    },
                    body: JSON.stringify(payload),
                  });

                  if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    throw new Error(errData.detail || "Submission failed.");
                  }

                  const data = await res.json();
                  setDraft({ donationId: data.donation_id });
                  toast.success("Items confirmed and saved!");
                  navigate({ to: "/donor/matches" });
                } catch (err) {
                  console.error(err);
                  toast.error(err instanceof Error ? err.message : "Failed to confirm items.");
                }
              }}
            >
              Confirm Items &amp; Find NGOs <ArrowRight className="h-4 w-4" />
            </Button>
          </Card>
        </div>
      </div>
    </DashboardShell>
  );
}

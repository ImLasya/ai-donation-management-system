import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader } from "@/components/shared/ui";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CATEGORIES } from "@/data/mock";
import { toast } from "sonner";
import { PlusCircle, Trash2, Package, AlertCircle } from "lucide-react";

export const Route = createFileRoute("/ngo/demands/new")({
  head: () => ({ meta: [{ title: "Create Demand — Donate" }] }),
  component: NewDemand,
});

const PRIORITIES = ["LOW", "MEDIUM", "HIGH", "URGENT"] as const;
type Priority = (typeof PRIORITIES)[number];

const CONDITIONS = ["NEW", "GOOD", "FAIR", "POOR"] as const;
type Condition = (typeof CONDITIONS)[number];

interface DemandItemRow {
  id: number;
  item_name: string;
  category: string;
  quantity_needed: number;
  acceptable_conditions: Condition[];
}

let _rowId = 0;
const nextId = () => ++_rowId;

const emptyItem = (): DemandItemRow => ({
  id: nextId(),
  item_name: "",
  category: CATEGORIES[0].name,
  quantity_needed: 1,
  acceptable_conditions: ["NEW", "GOOD"],
});

function NewDemand() {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<Priority>("MEDIUM");
  const [neededBy, setNeededBy] = useState("");
  const [items, setItems] = useState<DemandItemRow[]>([emptyItem()]);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // --- Item helpers ---
  const addItem = () => setItems((prev) => [...prev, emptyItem()]);

  const removeItem = (id: number) =>
    setItems((prev) => prev.filter((it) => it.id !== id));

  const updateItem = (id: number, patch: Partial<DemandItemRow>) =>
    setItems((prev) =>
      prev.map((it) => (it.id === id ? { ...it, ...patch } : it))
    );

  const toggleCondition = (rowId: number, cond: Condition) => {
    setItems((prev) =>
      prev.map((it) => {
        if (it.id !== rowId) return it;
        const has = it.acceptable_conditions.includes(cond);
        const next = has
          ? it.acceptable_conditions.filter((c) => c !== cond)
          : [...it.acceptable_conditions, cond];
        return { ...it, acceptable_conditions: next };
      })
    );
  };

  // --- Validation ---
  const validate = (): boolean => {
    const errs: Record<string, string> = {};
    if (!title.trim()) errs.title = "Demand title is required.";
    if (items.length === 0) errs.items = "Add at least one needed item.";
    items.forEach((it, idx) => {
      if (!it.item_name.trim())
        errs[`item_name_${idx}`] = "Item name is required.";
      if (it.quantity_needed <= 0)
        errs[`qty_${idx}`] = "Quantity must be at least 1.";
    });
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  // --- Submit ---
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) {
      toast.error("Please fix the errors before submitting.");
      // Automatically scroll to the first validation error (e.g. missing title)
      setTimeout(() => {
        const firstErrorEl = document.querySelector(".text-destructive");
        if (firstErrorEl) {
          firstErrorEl.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }, 100);
      return;
    }
    setSubmitting(true);

    const payload = {
      title: title.trim(),
      description: description.trim() || undefined,
      priority,
      needed_by: neededBy || undefined,
      status: "OPEN",
      items: items.map((it) => ({
        item_name: it.item_name.trim(),
        category: it.category,
        quantity_needed: it.quantity_needed,
        acceptable_conditions: it.acceptable_conditions,
      })),
    };

    try {
      const token = localStorage.getItem("da_token");
      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/api/donations/demands`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(payload),
        }
      );

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Server error: ${res.status}`);
      }

      const data = await res.json();
      toast.success(`Demand "${data.title || title}" created successfully!`);
      navigate({ to: "/ngo/demands" });
    } catch (err) {
      console.error(err);
      toast.error(err instanceof Error ? err.message : "Failed to create demand.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <DashboardShell role="ngo">
      <PageHeader
        title="Create Demand"
        subtitle="Define what items your NGO currently needs."
      />

      <form onSubmit={handleSubmit} noValidate className="space-y-6 max-w-3xl">
        {/* ── Demand Details Card ── */}
        <Card className="p-6">
          <h2 className="text-base font-semibold text-foreground mb-4">
            Demand Details
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {/* Title */}
            <div className="sm:col-span-2">
              <Label htmlFor="demand-title">
                Demand Title <span className="text-destructive">*</span>
              </Label>
              <Input
                id="demand-title"
                className="mt-1"
                value={title}
                onChange={(e) => {
                  setTitle(e.target.value);
                  if (errors.title) setErrors((p) => ({ ...p, title: "" }));
                }}
                placeholder="e.g. School Supplies Needed"
              />
              {errors.title && (
                <p className="mt-1 text-xs text-destructive flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" />
                  {errors.title}
                </p>
              )}
            </div>

            {/* Description */}
            <div className="sm:col-span-2">
              <Label htmlFor="demand-description">Description</Label>
              <Textarea
                id="demand-description"
                className="mt-1 min-h-[80px]"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Briefly describe who these items are for and why they are needed…"
              />
            </div>

            {/* Priority */}
            <div>
              <Label htmlFor="demand-priority">Priority</Label>
              <Select
                value={priority}
                onValueChange={(v) => setPriority(v as Priority)}
              >
                <SelectTrigger id="demand-priority" className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PRIORITIES.map((p) => (
                    <SelectItem key={p} value={p}>
                      {p.charAt(0) + p.slice(1).toLowerCase()}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Needed by date */}
            <div>
              <Label htmlFor="demand-needed-by">Needed By Date</Label>
              <Input
                id="demand-needed-by"
                type="date"
                className="mt-1"
                value={neededBy}
                onChange={(e) => setNeededBy(e.target.value)}
              />
            </div>
          </div>
        </Card>

        {/* ── Needed Items Card ── */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
              <Package className="h-4 w-4 text-primary" />
              Needed Items
              <span className="ml-1 text-sm font-normal text-muted-foreground">
                ({items.length})
              </span>
            </h2>
            <Button
              type="button"
              variant="outline"
              size="sm"
              id="add-item-btn"
              className="gap-1"
              onClick={addItem}
            >
              <PlusCircle className="h-4 w-4" />
              Add Item
            </Button>
          </div>

          {errors.items && (
            <p className="mb-3 text-xs text-destructive flex items-center gap-1">
              <AlertCircle className="h-3 w-3" />
              {errors.items}
            </p>
          )}

          <div className="space-y-4">
            {items.map((row, idx) => (
              <div
                key={row.id}
                className="relative rounded-lg border border-border bg-muted/30 p-4"
              >
                {/* Row header */}
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                    Item {idx + 1}
                  </span>
                  {items.length > 1 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      id={`remove-item-${row.id}`}
                      onClick={() => removeItem(row.id)}
                      aria-label="Remove item"
                    >
                      <Trash2 className="h-3.5 w-3.5 text-destructive" />
                    </Button>
                  )}
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  {/* Item name */}
                  <div>
                    <Label htmlFor={`item-name-${row.id}`}>
                      Item Name <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id={`item-name-${row.id}`}
                      className="mt-1"
                      value={row.item_name}
                      onChange={(e) => {
                        updateItem(row.id, { item_name: e.target.value });
                        if (errors[`item_name_${idx}`])
                          setErrors((p) => ({
                            ...p,
                            [`item_name_${idx}`]: "",
                          }));
                      }}
                      placeholder="e.g. Mathematics Textbook"
                    />
                    {errors[`item_name_${idx}`] && (
                      <p className="mt-1 text-xs text-destructive">
                        {errors[`item_name_${idx}`]}
                      </p>
                    )}
                  </div>

                  {/* Category */}
                  <div>
                    <Label htmlFor={`item-cat-${row.id}`}>Category</Label>
                    <Select
                      value={row.category}
                      onValueChange={(v) => updateItem(row.id, { category: v })}
                    >
                      <SelectTrigger id={`item-cat-${row.id}`} className="mt-1">
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

                  {/* Quantity */}
                  <div>
                    <Label htmlFor={`item-qty-${row.id}`}>
                      Quantity Needed <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id={`item-qty-${row.id}`}
                      type="number"
                      min={1}
                      className="mt-1"
                      value={row.quantity_needed}
                      onChange={(e) => {
                        updateItem(row.id, {
                          quantity_needed: Math.max(1, Number(e.target.value)),
                        });
                        if (errors[`qty_${idx}`])
                          setErrors((p) => ({ ...p, [`qty_${idx}`]: "" }));
                      }}
                    />
                    {errors[`qty_${idx}`] && (
                      <p className="mt-1 text-xs text-destructive">
                        {errors[`qty_${idx}`]}
                      </p>
                    )}
                  </div>

                  {/* Acceptable conditions */}
                  <div>
                    <Label>Acceptable Conditions</Label>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {CONDITIONS.map((cond) => {
                        const active = row.acceptable_conditions.includes(cond);
                        return (
                          <button
                            key={cond}
                            type="button"
                            id={`cond-${row.id}-${cond}`}
                            onClick={() => toggleCondition(row.id, cond)}
                            className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                              active
                                ? "border-primary bg-primary text-primary-foreground"
                                : "border-border bg-background text-muted-foreground hover:border-primary/50"
                            }`}
                          >
                            {cond.charAt(0) + cond.slice(1).toLowerCase()}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Bottom add item */}
          <Button
            type="button"
            variant="outline"
            className="mt-4 w-full gap-2 border-dashed border-2"
            id="add-item-bottom-btn"
            onClick={addItem}
          >
            <PlusCircle className="h-4 w-4" />
            Add Another Item
          </Button>
        </Card>

        {/* ── Actions ── */}
        <div className="flex gap-3">
          <Button
            type="submit"
            id="submit-demand-btn"
            disabled={submitting}
            className="min-w-[140px]"
          >
            {submitting ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                Submitting…
              </span>
            ) : (
              "Submit Demand"
            )}
          </Button>
          <Button
            type="button"
            variant="outline"
            id="cancel-demand-btn"
            disabled={submitting}
            onClick={() => navigate({ to: "/ngo/demands" })}
          >
            Cancel
          </Button>
        </div>
      </form>
    </DashboardShell>
  );
}

import { createFileRoute } from "@tanstack/react-router";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, StatusBadge } from "@/components/shared/ui";
import { Card } from "@/components/ui/card";
import { INVENTORY } from "@/data/mock";
import { AlertTriangle } from "lucide-react";

export const Route = createFileRoute("/ngo/inventory")({
  head: () => ({ meta: [{ title: "Inventory — Donate" }] }),
  component: Inventory,
});

function Inventory() {
  return (
    <DashboardShell role="ngo">
      <PageHeader title="Inventory" subtitle="Track received items and distribution status." />
      <Card className="overflow-x-auto p-0">
        <table className="w-full min-w-[640px] text-sm">
          <thead className="border-b border-border bg-muted/40 text-left text-xs text-muted-foreground">
            <tr>
              {["Item", "Category", "Qty", "Source", "Received", "Status"].map((h) => (
                <th key={h} className="px-4 py-3 font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {INVENTORY.map((it) => (
              <tr key={it.id} className="border-b border-border last:border-0">
                <td className="px-4 py-3 font-medium text-foreground">
                  <span className="flex items-center gap-2">
                    {it.name}
                    {it.quantity < 10 && (
                      <AlertTriangle className="h-3.5 w-3.5 text-accent" aria-label="Low stock" />
                    )}
                  </span>
                </td>
                <td className="px-4 py-3 text-muted-foreground">{it.category}</td>
                <td className="px-4 py-3 text-foreground">{it.quantity}</td>
                <td className="px-4 py-3 text-muted-foreground">{it.source}</td>
                <td className="px-4 py-3 text-muted-foreground">{it.receivedDate}</td>
                <td className="px-4 py-3">
                  <StatusBadge
                    status={
                      it.distributionStatus === "In Stock"
                        ? "Active"
                        : it.distributionStatus === "Distributed"
                          ? "Fulfilled"
                          : "Medium"
                    }
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </DashboardShell>
  );
}

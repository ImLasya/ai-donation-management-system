import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, StatusBadge } from "@/components/shared/ui";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DONATIONS } from "@/data/mock";
import { Search, ArrowRight } from "lucide-react";

export const Route = createFileRoute("/donor/donations")({
  head: () => ({ meta: [{ title: "My Donations — Donate" }] }),
  component: Donations,
});

function Donations() {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("all");
  const [donations, setDonations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDonations = async () => {
      try {
        const token = localStorage.getItem("da_token");
        const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/donations/list`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        if (res.ok) {
          const data = await res.json();
          setDonations(data);
        }
      } catch (err) {
        console.error("Failed to load donations:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchDonations();
  }, []);

  const list = donations.filter(
    (d) =>
      (status === "all" || d.status === status) &&
      (d.ngoName.toLowerCase().includes(q.toLowerCase()) ||
        d.id.toLowerCase().includes(q.toLowerCase())),
  );

  return (
    <DashboardShell role="donor">
      <PageHeader
        title="My Donations"
        subtitle="Search, filter, and track your donation history."
      />
      <div className="mb-5 flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-52">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search donations…"
            className="pl-9"
          />
        </div>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="w-44">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {["Collected", "Delivered", "Acknowledged"].map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="grid gap-4">
        {list.map((d) => (
          <Card
            key={d.id}
            className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <p className="font-semibold text-foreground">{d.id}</p>
                <StatusBadge status={d.status} />
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                {d.ngoName} · {d.date}
              </p>
              <div className="mt-2 flex flex-wrap gap-1">
                {d.items.map((it) => (
                  <span
                    key={it.id}
                    className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground"
                  >
                    {it.label} ×{it.quantity}
                  </span>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-4 sm:flex-col sm:items-end">
              <span className="text-sm text-muted-foreground">{d.beneficiaries} helped</span>
              <Button asChild size="sm" variant="outline" className="gap-1">
                <Link to="/donor/track/$id" params={{ id: d.id }}>
                  Track <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </DashboardShell>
  );
}

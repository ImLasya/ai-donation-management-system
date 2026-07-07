import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader } from "@/components/shared/ui";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge, ScoreBar } from "@/components/shared/ui";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useApp } from "@/context/AppContext";
import {
  HeartHandshake,
  MapPin,
  ShieldCheck,
  ArrowRight,
  Sparkles,
  Filter,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Package,
  AlertTriangle,
  History,
} from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/donor/matches")({
  head: () => ({ meta: [{ title: "NGO Matches — Donate" }] }),
  component: Matches,
});

interface MatchedItemDetail {
  donated_item: string;
  demand_item: string;
  donated_quantity: number;
  remaining_needed: number;
  semantic_similarity: number;
  match_type: string;
  condition_status: string;
}

interface MatchBreakdown {
  itemTypeMatch: number;
  quantityFit: number;
  proximity: number;
  ngoPriority: number;
}

interface NGOInfo {
  id: number;
  name: string;
  city: string;
  distanceKm: number;
  verified: boolean;
}

interface DonationMatchResponse {
  match_id: number;
  demand_id: number;
  demand_title: string;
  final_score: number;
  item_match_score: number;
  quantity_fit_score: number;
  geographic_score: number;
  priority_score: number;
  matched_items: MatchedItemDetail[];
  reasons: string[];
  
  // Legacy compat
  id: string; // ngo user id
  overallScore: number;
  urgency: string;
  demandExpiry: string;
  itemsNeeded: string[];
  ngo: NGOInfo;
  breakdown: MatchBreakdown;
}

function Matches() {
  const { draft } = useApp();
  const navigate = useNavigate();
  const [sort, setSort] = useState("best");
  const [onlyVerified, setOnlyVerified] = useState(false);
  const [matches, setMatches] = useState<DonationMatchResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedMatchId, setExpandedMatchId] = useState<number | null>(null);

  // Read donation ID from route or context draft state
  const activeDonationId = draft.donationId;

  useEffect(() => {
    const fetchMatches = async () => {
      if (!activeDonationId) {
        setLoading(false);
        return;
      }
      try {
        const token = localStorage.getItem("da_token");
        const res = await fetch(
          `${import.meta.env.VITE_API_BASE_URL}/api/donations/matches?donation_id=${activeDonationId}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );
        if (res.ok) {
          const data = await res.json();
          setMatches(data);
        } else {
          toast.error("Failed to load match results.");
        }
      } catch (err) {
        console.error("Failed to load matches:", err);
        toast.error("Error retrieving intelligent matches.");
      } finally {
        setLoading(false);
      }
    };
    fetchMatches();
  }, [activeDonationId]);

  const toggleExpand = (matchId: number) => {
    setExpandedMatchId((prev) => (prev === matchId ? null : matchId));
  };

  const select = async (ngoUserId: number, ngoName: string) => {
    if (!activeDonationId) {
      toast.error("No active donation draft found. Please submit items first.");
      return;
    }

    try {
      const token = localStorage.getItem("da_token");
      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/api/donations/${activeDonationId}/requests`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ ngo_id: ngoUserId }),
        }
      );

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to send request.");
      }

      toast.success(`Donation request sent to ${ngoName}`);
      // Navigate to donation tracking page as requested (do not go to packaging yet)
      navigate({ to: `/donor/track/${activeDonationId}` });
    } catch (err) {
      console.error(err);
      toast.error(err instanceof Error ? err.message : "Failed to send request.");
    }
  };

  if (!activeDonationId) {
    return (
      <DashboardShell role="donor">
        <PageHeader
          title="Intelligent NGO Matches"
          subtitle="View NGOs matching your submitted donations."
        />
        <Card className="flex flex-col items-center justify-center p-12 text-center border-dashed">
          <History className="h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-semibold text-foreground">No active submission found</h3>
          <p className="mt-2 text-sm text-muted-foreground max-w-sm mb-6">
            Please submit your reviewed items from the Donate page first to search matching NGO demands.
          </p>
          <Button asChild>
            <Link to="/donor/donate">Go to Donate Items</Link>
          </Button>
        </Card>
      </DashboardShell>
    );
  }

  let list = [...matches];
  if (onlyVerified) list = list.filter((m) => m.ngo.verified);

  list.sort((a, b) => {
    if (sort === "nearest") {
      return a.ngo.distanceKm - b.ngo.distanceKm;
    } else if (sort === "priority") {
      return b.breakdown.ngoPriority - a.breakdown.ngoPriority;
    } else {
      return b.final_score - a.final_score;
    }
  });

  return (
    <DashboardShell role="donor">
      <PageHeader
        title="Intelligent NGO Matches"
        subtitle="NGOs ranked semantically by how well they match your submitted items."
      />

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Select value={sort} onValueChange={setSort}>
            <SelectTrigger className="w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="best">Best Match</SelectItem>
              <SelectItem value="nearest">Nearest</SelectItem>
              <SelectItem value="priority">Highest Priority</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Button
          variant={onlyVerified ? "default" : "outline"}
          size="sm"
          onClick={() => setOnlyVerified((v) => !v)}
          className="gap-2"
        >
          <ShieldCheck className="h-4 w-4" /> Verified only
        </Button>
      </div>

      {loading ? (
        <div className="grid gap-4">
          {[1, 2].map((i) => (
            <Card key={i} className="p-6 animate-pulse">
              <div className="h-6 w-1/3 rounded bg-muted mb-4" />
              <div className="h-4 w-2/3 rounded bg-muted mb-4" />
              <div className="h-8 w-24 rounded bg-muted" />
            </Card>
          ))}
        </div>
      ) : list.length === 0 ? (
        <Card className="flex flex-col items-center justify-center p-12 text-center border-dashed">
          <Sparkles className="h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-semibold text-foreground">No matches found</h3>
          <p className="mt-2 text-sm text-muted-foreground max-w-sm mb-6">
            We couldn't find any open demands that match your submitted items. Check back later or donate other items.
          </p>
          <Button asChild>
            <Link to="/donor/donations">My Donations</Link>
          </Button>
        </Card>
      ) : (
        <div className="space-y-5">
          {list.map((m) => {
            const isExpanded = expandedMatchId === m.match_id;
            const hasConditionPenalty = m.matched_items.some((it) =>
              it.condition_status.includes("penalty")
            );

            return (
              <Card key={m.match_id} className="p-6 transition-all duration-200 border-border hover:shadow-md">
                <div className="flex flex-col gap-6 lg:flex-row">
                  <div className="flex-1">
                    {/* Header */}
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className="grid h-12 w-12 place-items-center rounded-xl bg-primary/10 text-primary shrink-0">
                          <HeartHandshake className="h-6 w-6" />
                        </div>
                        <div>
                          <div className="flex items-center gap-1">
                            <p className="font-semibold text-foreground leading-tight">
                              {m.ngo.name}
                            </p>
                            {m.ngo.verified && (
                              <ShieldCheck className="h-4 w-4 text-primary shrink-0" title="Verified NGO" />
                            )}
                          </div>
                          <p className="flex items-center gap-1 text-xs text-muted-foreground mt-0.5">
                            <MapPin className="h-3 w-3" />
                            {m.ngo.city} · {m.ngo.distanceKm} km away
                          </p>
                        </div>
                      </div>
                      <div className="text-right shrink-0">
                        <p className="text-2xl font-extrabold text-primary">{Math.round(m.final_score)}%</p>
                        <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">
                          Compatibility
                        </p>
                      </div>
                    </div>

                    {/* Metadata Row */}
                    <div className="mt-4 flex flex-wrap items-center gap-2">
                      <span className="text-xs font-medium text-foreground bg-muted px-2.5 py-1 rounded-md">
                        Demand: {m.demand_title}
                      </span>
                      <StatusBadge status={m.urgency} />
                      <span className="text-xs text-muted-foreground">Expires {m.demandExpiry}</span>
                    </div>

                    {/* Matched Items count summary */}
                    <p className="mt-3 text-sm text-foreground font-medium">
                      Matched {m.matched_items_count} item type(s) from your donation.
                    </p>

                    {/* Top Reason text */}
                    {m.reasons.length > 0 && (
                      <p className="mt-2 text-xs text-muted-foreground italic line-clamp-1">
                        Reason: {m.reasons[0].replace("✓ ", "")}
                      </p>
                    )}

                    {/* Actions */}
                    <div className="mt-5 flex flex-wrap gap-2">
                      <Button size="sm" onClick={() => select(m.ngo.id, m.ngo.name)}>
                        Select NGO
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => toggleExpand(m.match_id)}
                        className="gap-1.5"
                      >
                        {isExpanded ? "Hide Details" : "Why this match?"}
                        {isExpanded ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                  </div>

                  {/* Sidebar Compact breakdown */}
                  <div className="w-full space-y-3 rounded-xl bg-muted/40 p-4 lg:w-72 shrink-0">
                    <p className="flex items-center gap-1 text-xs font-semibold text-foreground">
                      <Sparkles className="h-3.5 w-3.5 text-primary" /> Match Breakdown
                    </p>
                    <ScoreBar label="Item Compatibility" value={Math.round(m.item_match_score)} />
                    <ScoreBar label="Quantity Fit" value={Math.round(m.quantity_fit_score)} />
                    <ScoreBar label="Geographic Proximity" value={Math.round(m.geographic_score)} />
                    <ScoreBar label="NGO Priority" value={Math.round(m.priority_score)} />
                  </div>
                </div>

                {/* Collapsible details panel */}
                {isExpanded && (
                  <div className="mt-6 border-t border-border pt-5 animate-in fade-in slide-in-from-top-3 duration-200">
                    <div className="grid gap-6 md:grid-cols-2">
                      {/* Matched Items Details */}
                      <div>
                        <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1 mb-3">
                          <Package className="h-3.5 w-3.5 text-primary" />
                          Matched Items Comparison
                        </h4>
                        <div className="space-y-3">
                          {m.matched_items.map((it, index) => {
                            const isPenalty = it.condition_status.includes("penalty");
                            return (
                              <div
                                key={index}
                                className="rounded-lg bg-muted/30 p-3 border border-border/50 text-sm"
                              >
                                <div className="flex items-center justify-between font-medium">
                                  <span>{it.donated_item}</span>
                                  <span className="text-muted-foreground text-xs font-normal">→</span>
                                  <span>{it.demand_item}</span>
                                </div>
                                <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                                  <div>
                                    <span className="font-medium text-foreground">Similarity: </span>
                                    {Math.round(it.semantic_similarity * 100)}% ({it.match_type})
                                  </div>
                                  <div>
                                    <span className="font-medium text-foreground">Qty: </span>
                                    {it.donated_quantity} offered / {it.remaining_needed} needed
                                  </div>
                                </div>
                                {isPenalty && (
                                  <div className="mt-2 text-[11px] text-orange-600 bg-orange-50 border border-orange-100 rounded px-2 py-1 flex items-start gap-1">
                                    <AlertTriangle className="h-3 w-3 shrink-0 mt-0.5" />
                                    <span>{it.condition_status}</span>
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      {/* Score reasons */}
                      <div>
                        <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1 mb-3">
                          <CheckCircle2 className="h-3.5 w-3.5 text-primary" />
                          Transparency Reasons
                        </h4>
                        <ul className="space-y-2.5">
                          {m.reasons.map((r, index) => (
                            <li
                              key={index}
                              className="flex items-start gap-2.5 text-sm text-foreground"
                            >
                              <span className="text-success text-base shrink-0 select-none">•</span>
                              <span>{r.replace("✓ ", "").replace("  - ", "")}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </DashboardShell>
  );
}

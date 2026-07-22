import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, StatusBadge } from "@/components/shared/ui";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Check, X, Calendar, MapPin, Phone, Clipboard, CheckCircle, ArrowRight, User } from "lucide-react";
import { toast } from "sonner";
import { Link } from "@tanstack/react-router";

export const Route = createFileRoute("/ngo/incoming")({
  head: () => ({ meta: [{ title: "Incoming & Active Donations — Donate" }] }),
  component: Incoming,
});

type ActiveTab = "pending" | "active" | "history";

function Incoming() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("pending");
  const [requests, setRequests] = useState<any[]>([]); // Pending requests
  const [donations, setDonations] = useState<any[]>([]); // Accepted/active/history donations
  const [loading, setLoading] = useState(true);
  const [volunteerInputs, setVolunteerInputs] = useState<Record<string, { name: string; phone: string; email: string }>>({});

  const fetchIncomingData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("da_token");
      // Fetch both pending requests and overall donation lists
      const [requestsRes, donationsRes] = await Promise.all([
        fetch(`${import.meta.env.VITE_API_BASE_URL}/api/donations/requests/incoming`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${import.meta.env.VITE_API_BASE_URL}/api/donations/list`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      if (requestsRes.ok) {
        const reqData = await requestsRes.json();
        setRequests(reqData);
      }
      if (donationsRes.ok) {
        const donData = await donationsRes.json();
        setDonations(donData);
      }
    } catch (err) {
      console.error("Failed to load incoming NGO data:", err);
      toast.error("Error loading dashboard data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncomingData();
  }, []);

  const handleAccept = async (id: number) => {
    try {
      const token = localStorage.getItem("da_token");
      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/api/donations/requests/${id}/accept`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        },
      );

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to accept request.");
      }

      toast.success("Donation request accepted successfully!");
      fetchIncomingData();
    } catch (err) {
      console.error(err);
      toast.error(err instanceof Error ? err.message : "Failed to accept request.");
    }
  };

  const handleReject = async (id: number) => {
    try {
      const token = localStorage.getItem("da_token");
      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/api/donations/requests/${id}/reject`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        },
      );

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to reject request.");
      }

      toast.success("Donation request declined.");
      fetchIncomingData();
    } catch (err) {
      console.error(err);
      toast.error(err instanceof Error ? err.message : "Failed to reject request.");
    }
  };

  const handleConfirmCollection = async (donationId: string) => {
    try {
      const token = localStorage.getItem("da_token");
      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/api/donations/${donationId}/transit`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        },
      );

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to confirm collection.");
      }

      toast.success("Collection confirmed! Donation status updated to In-Transit.");
      fetchIncomingData();
    } catch (err) {
      console.error(err);
      toast.error(err instanceof Error ? err.message : "Failed to confirm collection.");
    }
  };

  const handleMarkDelivered = async (donationId: string) => {
    try {
      const token = localStorage.getItem("da_token");
      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/api/donations/${donationId}/complete`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        },
      );

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to mark delivered.");
      }

      toast.success("Donation marked as delivered successfully.");
      fetchIncomingData();
    } catch (err) {
      console.error(err);
      toast.error(err instanceof Error ? err.message : "Failed to mark delivered.");
    }
  };

  const handleAcknowledgeReceipt = async (donationId: string) => {
    try {
      const token = localStorage.getItem("da_token");
      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/api/donations/${donationId}/acknowledge`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        },
      );

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to acknowledge receipt.");
      }

      toast.success("Receipt acknowledged! Final thank-you sent to donor.");
      fetchIncomingData();
    } catch (err) {
      console.error(err);
      toast.error(err instanceof Error ? err.message : "Failed to acknowledge receipt.");
    }
  };

  const handleAssignVolunteer = async (donationId: string) => {
    const inputs = volunteerInputs[donationId];
    const name = inputs?.name?.trim() || "";
    const phone = inputs?.phone?.trim() || "";
    const email = inputs?.email?.trim() || "";

    if (!name || !phone || !email) {
      toast.error("Please enter volunteer name, phone number, and email.");
      return;
    }

    try {
      const token = localStorage.getItem("da_token");
      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/api/donations/${donationId}/assign-volunteer`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            volunteer_name: name,
            volunteer_phone: phone,
            volunteer_email: email,
          }),
        },
      );

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to assign volunteer.");
      }

      toast.success("Volunteer assigned successfully!");
      // Reset inputs for this donation
      setVolunteerInputs(prev => ({
        ...prev,
        [donationId]: { name: "", phone: "", email: "" }
      }));
      fetchIncomingData();
    } catch (err) {
      console.error(err);
      toast.error(err instanceof Error ? err.message : "Failed to assign volunteer.");
    }
  };

  // Filter donations for active and history
  const activeDonations = donations.filter((d) =>
    ["NGO_ACCEPTED", "PACKAGING_IN_PROGRESS", "READY_FOR_PICKUP", "PICKUP_SCHEDULED", "COLLECTED", "DELIVERED", "PICKUP_IN_PROGRESS"].includes(d.status)
  );

  const historyDonations = donations.filter((d) =>
    ["ACKNOWLEDGED", "COMPLETED", "REJECTED"].includes(d.status)
  );

  return (
    <DashboardShell role="ngo">
      <PageHeader title="Donations Coordinator" subtitle="Review incoming requests, manage collections, and acknowledge receipts." />
      
      {/* Custom Tabs Navigation */}
      <div className="flex border-b border-border mb-6">
        <button
          onClick={() => setActiveTab("pending")}
          className={`px-4 py-2 text-sm font-semibold border-b-2 transition-all ${
            activeTab === "pending"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          Incoming Requests ({requests.length})
        </button>
        <button
          onClick={() => setActiveTab("active")}
          className={`px-4 py-2 text-sm font-semibold border-b-2 transition-all ${
            activeTab === "active"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          Active Collections ({activeDonations.length})
        </button>
        <button
          onClick={() => setActiveTab("history")}
          className={`px-4 py-2 text-sm font-semibold border-b-2 transition-all ${
            activeTab === "history"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          History Archive ({historyDonations.length})
        </button>
      </div>

      <div className="grid gap-4">
        {loading ? (
          <p className="text-muted-foreground">Loading data...</p>
        ) : activeTab === "pending" ? (
          // PENDING TAB
          requests.length === 0 ? (
            <Card className="p-8 text-center border-dashed">
              <p className="text-muted-foreground font-medium">
                No incoming donation requests at the moment.
              </p>
            </Card>
          ) : (
            requests.map((r) => (
              <Card key={r.id} className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-foreground">Request #{r.id}</p>
                    <StatusBadge status={r.status} />
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground font-medium">
                    Donor: <span className="font-semibold text-foreground">{r.donorName}</span> · City: {r.donorCity} · Date: {r.date}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {r.items.map((it: any) => (
                      <span key={it.id} className="rounded-full bg-muted px-2.5 py-0.5 text-xs text-muted-foreground font-medium">
                        {it.label} ×{it.quantity} ({it.condition})
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" className="gap-1 bg-teal-600 hover:bg-teal-700" onClick={() => handleAccept(r.id)}>
                    <Check className="h-4 w-4" /> Accept
                  </Button>
                  <Button size="sm" variant="outline" className="gap-1" onClick={() => handleReject(r.id)}>
                    <X className="h-4 w-4" /> Decline
                  </Button>
                </div>
              </Card>
            ))
          )
        ) : activeTab === "active" ? (
          // ACTIVE TAB
          activeDonations.length === 0 ? (
            <Card className="p-8 text-center border-dashed">
              <p className="text-muted-foreground font-medium">No active donation collection processes.</p>
            </Card>
          ) : (
            activeDonations.map((d) => (
              <Card key={d.id} className="p-5 flex flex-col gap-4">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-border pb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-semibold text-foreground">Donation DON-{d.id}</p>
                      <StatusBadge status={d.status} />
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">Donor: <span className="font-medium text-foreground">{d.donorName}</span> · Phone: {d.donorPhone || "N/A"}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Button asChild size="sm" variant="outline">
                      <Link to="/donor/track/$id" params={{ id: d.id }}>
                        Track Timeline <ArrowRight className="h-3.5 w-3.5 ml-1" />
                      </Link>
                    </Button>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  {/* Left: Items summary */}
                  <div>
                    <h4 className="text-xs font-bold uppercase text-muted-foreground mb-2">Item Checklist Summary</h4>
                    <div className="flex flex-wrap gap-1.5">
                      {d.items.map((it: any) => (
                        <span key={it.id} className="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground font-medium">
                          {it.label} (x{it.quantity}) - {it.condition}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Right: Pickup Info & Transitions */}
                  <div className="border-t md:border-t-0 md:border-l border-border pt-4 md:pt-0 md:pl-4 space-y-3">
                    <h4 className="text-xs font-bold uppercase text-muted-foreground">Pickup Coordination</h4>
                    {d.pickup ? (
                      <div className="space-y-1.5 text-sm">
                        <p className="flex items-center gap-2 text-foreground font-medium">
                          <Calendar className="h-4 w-4 text-primary shrink-0" />
                          {d.pickup.date} at {d.pickup.timeSlot}
                        </p>
                        <p className="flex items-center gap-2 text-muted-foreground text-xs">
                          <MapPin className="h-4 w-4 text-muted-foreground shrink-0" />
                          {d.pickup.address}
                        </p>
                        <p className="flex items-center gap-2 text-muted-foreground text-xs">
                          <Phone className="h-4 w-4 text-muted-foreground shrink-0" />
                          Contact: {d.pickup.phone}
                        </p>
                        {d.pickup.notes && (
                          <p className="flex items-center gap-2 text-muted-foreground text-xs italic">
                            <Clipboard className="h-4 w-4 text-muted-foreground shrink-0" />
                            Notes: "{d.pickup.notes}"
                          </p>
                        )}
                        
                        {/* Interactive Volunteer Assignment Form */}
                        <div className="mt-3 border-t border-border pt-3 space-y-2">
                          <h5 className="text-[11px] font-bold uppercase text-muted-foreground flex items-center gap-1">
                            <User className="h-3 w-3" /> Assign/Update Courier Volunteer
                          </h5>
                          {d.pickup.volunteerName ? (
                            <p className="text-xs text-foreground font-semibold bg-muted/50 p-2 rounded border border-border">
                              Assigned: <span className="text-primary font-bold">{d.pickup.volunteerName}</span> · Phone: <span className="font-bold">{d.pickup.volunteerPhone}</span>
                            </p>
                          ) : (
                            <p className="text-xs text-muted-foreground italic">No volunteer assigned to collect this package yet.</p>
                          )}
                          <div className="flex flex-col gap-2">
                            <div className="flex gap-2">
                              <Input
                                placeholder="Name"
                                className="h-8 text-xs max-w-[130px]"
                                value={volunteerInputs[d.id]?.name || ""}
                                onChange={(e) => setVolunteerInputs(prev => ({
                                  ...prev,
                                  [d.id]: { ...prev[d.id], name: e.target.value, phone: prev[d.id]?.phone || "", email: prev[d.id]?.email || "" }
                                }))}
                              />
                              <Input
                                placeholder="Phone"
                                className="h-8 text-xs max-w-[130px]"
                                value={volunteerInputs[d.id]?.phone || ""}
                                onChange={(e) => setVolunteerInputs(prev => ({
                                  ...prev,
                                  [d.id]: { ...prev[d.id], name: prev[d.id]?.name || "", phone: e.target.value, email: prev[d.id]?.email || "" }
                                }))}
                              />
                            </div>
                            <div className="flex gap-2">
                              <Input
                                placeholder="Volunteer Email"
                                type="email"
                                className="h-8 text-xs flex-1"
                                value={volunteerInputs[d.id]?.email || ""}
                                onChange={(e) => setVolunteerInputs(prev => ({
                                  ...prev,
                                  [d.id]: { ...prev[d.id], name: prev[d.id]?.name || "", phone: prev[d.id]?.phone || "", email: e.target.value }
                                }))}
                              />
                              <Button size="sm" className="h-8 text-xs bg-primary hover:bg-primary/90" onClick={() => handleAssignVolunteer(d.id)}>
                                Save
                              </Button>
                            </div>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <p className="text-xs text-muted-foreground italic">Waiting for donor to schedule pickup time and location.</p>
                    )}

                    {/* Transition Actions */}
                    <div className="pt-2">
                      {d.status === "PICKUP_SCHEDULED" && (
                        <Button className="w-full gap-1.5 bg-orange-600 hover:bg-orange-700" onClick={() => handleConfirmCollection(d.id)}>
                          <Clipboard className="h-4 w-4" /> Confirm Collection (Mark Collected)
                        </Button>
                      )}
                      {d.status === "COLLECTED" && (
                        <Button className="w-full gap-1.5 bg-blue-600 hover:bg-blue-700" onClick={() => handleMarkDelivered(d.id)}>
                          <CheckCircle className="h-4 w-4" /> Mark Delivered (Mark Delivered)
                        </Button>
                      )}
                      {d.status === "DELIVERED" && (
                        <Button className="w-full gap-1.5 bg-teal-600 hover:bg-teal-700" onClick={() => handleAcknowledgeReceipt(d.id)}>
                          <CheckCircle className="h-4 w-4" /> Acknowledge Receipt (Complete Workflow)
                        </Button>
                      )}
                      {!["PICKUP_SCHEDULED", "COLLECTED", "DELIVERED"].includes(d.status) && (
                        <p className="text-xs text-muted-foreground bg-muted p-2 rounded text-center">
                          Waiting for donor completion: <strong>{d.status.replace(/_/g, " ")}</strong>
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            ))
          )
        ) : (
          // HISTORY TAB
          historyDonations.length === 0 ? (
            <Card className="p-8 text-center border-dashed">
              <p className="text-muted-foreground font-medium">No archived donations found.</p>
            </Card>
          ) : (
            historyDonations.map((d) => (
              <Card key={d.id} className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-foreground">Donation DON-{d.id}</p>
                    <StatusBadge status={d.status} />
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Donor: <span className="font-semibold text-foreground">{d.donorName}</span> · Date: {d.date}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {d.items.map((it: any) => (
                      <span key={it.id} className="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground font-medium">
                        {it.label} (x{it.quantity})
                      </span>
                    ))}
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <span className="text-xs text-muted-foreground block">Completed Journey</span>
                  <Button asChild variant="outline" size="sm" className="mt-1">
                    <Link to="/donor/track/$id" params={{ id: d.id }}>View Tracking</Link>
                  </Button>
                </div>
              </Card>
            ))
          )
        )}
      </div>
    </DashboardShell>
  );
}

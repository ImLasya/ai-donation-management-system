import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader } from "@/components/shared/ui";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useApp } from "@/context/AppContext";
import { cn } from "@/lib/utils";
import { CalendarCheck, CheckCircle2, MapPin } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/donor/schedule")({
  head: () => ({ meta: [{ title: "Schedule Pickup — Donate" }] }),
  component: Schedule,
});

const SLOTS = [
  "09:00 AM – 11:00 AM",
  "11:00 AM – 01:00 PM",
  "02:00 PM – 04:00 PM",
  "04:00 PM – 06:00 PM",
];

function Schedule() {
  const { draft } = useApp();
  const navigate = useNavigate();
  const [date, setDate] = useState("");
  const [slot, setSlot] = useState("");
  const [address, setAddress] = useState("42 MG Road, Bengaluru, Karnataka 560001");
  const [phone, setPhone] = useState("+91 98765 43210");
  const [notes, setNotes] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const pickupId = "PU-" + Math.floor(1000 + Math.random() * 9000);

  if (confirmed) {
    return (
      <DashboardShell role="donor">
        <div className="mx-auto max-w-lg">
          <Card className="p-8 text-center">
            <CheckCircle2 className="mx-auto h-14 w-14 text-success" />
            <h1 className="mt-4 text-2xl font-bold text-foreground">Pickup Confirmed!</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Your donation pickup has been scheduled.
            </p>
            <dl className="mt-6 space-y-3 rounded-xl bg-muted/40 p-4 text-left text-sm">
              <Row label="Pickup ID" value={pickupId} />
              <Row label="Date" value={date || "Jul 8, 2026"} />
              <Row label="Time" value={slot || SLOTS[0]} />
              <Row label="Address" value={address} />
              <Row label="NGO" value={draft.selectedMatch?.ngo.name ?? "Hope Foundation"} />
              <Row label="Items" value={`${draft.items.length || 2} item types`} />
            </dl>
            <div className="mt-6 flex flex-col gap-2 sm:flex-row">
              <Button
                variant="outline"
                className="flex-1 gap-2"
                onClick={() => alert("Calendar event created (demo)")}
              >
                <CalendarCheck className="h-4 w-4" /> Add to Calendar
              </Button>
              <Button
                className="flex-1"
                onClick={() =>
                  navigate({ to: "/donor/track/$id", params: { id: String(draft.donationId) } })
                }
              >
                Track Donation
              </Button>
            </div>
          </Card>
        </div>
      </DashboardShell>
    );
  }

  return (
    <DashboardShell role="donor">
      <PageHeader
        title="Schedule Pickup"
        subtitle="Choose a date, time slot, and address for collection."
      />
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card className="p-6">
            <Label htmlFor="date">Pickup date</Label>
            <Input
              id="date"
              type="date"
              className="mt-1 max-w-xs"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
            <p className="mb-2 mt-6 text-sm font-medium text-foreground">Available time slots</p>
            <div className="grid gap-3 sm:grid-cols-2">
              {SLOTS.map((s) => (
                <button
                  key={s}
                  onClick={() => setSlot(s)}
                  className={cn(
                    "rounded-lg border p-3 text-sm font-medium transition-colors",
                    slot === s
                      ? "border-primary bg-primary/5 text-primary"
                      : "border-border text-foreground hover:bg-muted/40",
                  )}
                >
                  {s}
                </button>
              ))}
            </div>
          </Card>
          <Card className="p-6">
            <Label htmlFor="addr" className="flex items-center gap-2">
              <MapPin className="h-4 w-4" /> Pickup address
            </Label>
            <Textarea
              id="addr"
              className="mt-1"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
            />
            <Label htmlFor="phone" className="mt-4 block">
              Contact Phone
            </Label>
            <Input
              id="phone"
              className="mt-1"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="e.g. +91 98765 43210"
            />
            <Label htmlFor="notes" className="mt-4 block">
              Special instructions (optional)
            </Label>
            <Input
              id="notes"
              className="mt-1"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Ring the doorbell, apartment 3B"
            />
          </Card>
        </div>
        <div>
          <Card className="sticky top-24 p-6">
            <h3 className="font-semibold text-foreground">Pickup summary</h3>
            <dl className="mt-4 space-y-2 text-sm">
              <Row label="NGO" value={draft.selectedMatch?.ngo.name ?? "Hope Foundation"} />
              <Row label="Items" value={`${draft.items.length || 2} types`} />
              <Row label="Packaging" value={draft.packagingDone ? "Ready" : "Pending"} />
            </dl>
            <Button
              className="mt-5 w-full"
              disabled={!date || !slot || !phone || !address}
              onClick={async () => {
                const donationId = draft.donationId;
                if (!donationId) {
                  toast.error("No active donation found. Please submit items first.");
                  return;
                }

                try {
                  const token = localStorage.getItem("da_token");
                  const res = await fetch(
                    `${import.meta.env.VITE_API_BASE_URL}/api/donations/${donationId}/pickup`,
                    {
                      method: "POST",
                      headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${token}`,
                      },
                      body: JSON.stringify({
                        pickup_date: date,
                        time_slot: slot,
                        pickup_address: address,
                        contact_phone: phone,
                        notes: notes,
                      }),
                    },
                  );

                  if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    throw new Error(errData.detail || "Failed to schedule pickup.");
                  }

                  toast.success("Pickup scheduled successfully!");
                  setConfirmed(true);
                } catch (err) {
                  console.error(err);
                  toast.error(err instanceof Error ? err.message : "Failed to schedule pickup.");
                }
              }}
            >
              Confirm Pickup
            </Button>
          </Card>
        </div>
      </div>
    </DashboardShell>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-right font-medium text-foreground">{value}</dd>
    </div>
  );
}

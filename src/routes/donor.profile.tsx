import { createFileRoute } from "@tanstack/react-router";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, SectionCard } from "@/components/shared/ui";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useApp } from "@/context/AppContext";
import { userService } from "@/services";
import { toast } from "sonner";
import { useState, useEffect } from "react";
import { Loader2 } from "lucide-react";

export const Route = createFileRoute("/donor/profile")({
  head: () => ({ meta: [{ title: "Profile & Settings — Donate" }] }),
  component: Profile,
});

function Profile() {
  const { user, updateUser } = useApp();
  const [saving, setSaving] = useState(false);

  // Controlled form state - pre-populated from current user
  const [form, setForm] = useState({
    name: user?.name ?? "",
    email: user?.email ?? "",
    phone: user?.phone ?? "",
    city: user?.city ?? "",
    state: user?.state ?? "",
  });

  // Sync form if user loads after initial render
  useEffect(() => {
    if (user) {
      setForm({
        name: user.name ?? "",
        email: user.email ?? "",
        phone: user.phone ?? "",
        city: user.city ?? "",
        state: user.state ?? "",
      });
    }
  }, [user?.id]);

  const handleChange = (field: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) {
      toast.error("Name cannot be empty.");
      return;
    }
    setSaving(true);
    try {
      const updated = await userService.updateProfile({
        name: form.name.trim(),
        phone: form.phone.trim(),
        city: form.city.trim(),
        state: form.state.trim(),
      });
      // Reflect new values immediately in sidebar / header
      updateUser({
        name: updated.name ?? form.name,
        phone: updated.phone ?? form.phone,
        city: updated.city ?? form.city,
        state: updated.state ?? form.state,
      });
      toast.success("Profile saved successfully!");
    } catch (err: any) {
      const msg = err?.message || "Failed to save profile. Please try again.";
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  const channels = [
    "Email notifications",
    "SMS notifications",
    "WhatsApp notifications",
    "In-app notifications",
  ];

  return (
    <DashboardShell role="donor">
      <PageHeader title="Profile & Settings" subtitle="Manage your account and preferences." />
      <form className="grid gap-6 lg:grid-cols-2" onSubmit={handleSubmit}>
        <SectionCard title="Personal Information">
          <div className="space-y-4">
            <div>
              <Label htmlFor="profile-name">Name</Label>
              <Input
                id="profile-name"
                className="mt-1"
                value={form.name}
                onChange={handleChange("name")}
                placeholder="Your full name"
                required
              />
            </div>
            <div>
              <Label htmlFor="profile-email">Email</Label>
              <Input
                id="profile-email"
                type="email"
                className="mt-1"
                value={form.email}
                disabled
                title="Email cannot be changed after registration."
              />
              <p className="mt-1 text-xs text-muted-foreground">Email cannot be changed.</p>
            </div>
            <div>
              <Label htmlFor="profile-phone">Phone</Label>
              <Input
                id="profile-phone"
                className="mt-1"
                value={form.phone}
                onChange={handleChange("phone")}
                placeholder="+91 98765 43210"
              />
            </div>
            <div>
              <Label htmlFor="profile-city">City</Label>
              <Input
                id="profile-city"
                className="mt-1"
                value={form.city}
                onChange={handleChange("city")}
                placeholder="City"
              />
            </div>
            <div>
              <Label htmlFor="profile-state">State</Label>
              <Input
                id="profile-state"
                className="mt-1"
                value={form.state}
                onChange={handleChange("state")}
                placeholder="State"
              />
            </div>
          </div>
        </SectionCard>

        <SectionCard title="Notification Preferences">
          <div className="space-y-4">
            {channels.map((c) => (
              <div key={c} className="flex items-center justify-between">
                <Label className="font-normal">{c}</Label>
                <Switch defaultChecked={!c.includes("WhatsApp")} />
              </div>
            ))}
            <p className="rounded-lg bg-muted p-3 text-xs text-muted-foreground">
              SMS & WhatsApp delivery connect to Twilio in the backend integration.
            </p>
          </div>
        </SectionCard>

        <div className="flex items-center gap-3 lg:col-span-2">
          <Button type="submit" disabled={saving} className="gap-2">
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            {saving ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </form>
    </DashboardShell>
  );
}

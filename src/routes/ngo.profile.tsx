import { createFileRoute } from "@tanstack/react-router";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, SectionCard } from "@/components/shared/ui";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useApp } from "@/context/AppContext";
import { userService } from "@/services";
import { toast } from "sonner";
import { useState, useEffect } from "react";
import { Loader2 } from "lucide-react";

export const Route = createFileRoute("/ngo/profile")({
  head: () => ({ meta: [{ title: "NGO Profile — Donate" }] }),
  component: NGOProfile,
});

function NGOProfile() {
  const { user, updateUser } = useApp();
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    orgName: user?.org ?? "",
    registrationNumber: user?.registrationNumber ?? "",
    contactPerson: user?.contactPerson ?? user?.name ?? "",
    email: user?.email ?? "",
    phone: user?.phone ?? "",
    address: user?.address ?? "",
    city: user?.city ?? "",
    state: user?.state ?? "",
    mission: user?.mission ?? "",
  });

  useEffect(() => {
    if (user) {
      setForm({
        orgName: user.org ?? "",
        registrationNumber: user.registrationNumber ?? "",
        contactPerson: user.contactPerson ?? user.name ?? "",
        email: user.email ?? "",
        phone: user.phone ?? "",
        address: user.address ?? "",
        city: user.city ?? "",
        state: user.state ?? "",
        mission: user.mission ?? "",
      });
    }
  }, [user?.id]);

  const handleChange = (field: keyof typeof form) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.contactPerson.trim()) {
      toast.error("Contact person name cannot be empty.");
      return;
    }
    setSaving(true);
    try {
      const updated = await userService.updateProfile({
        contactPerson: form.contactPerson.trim(),
        phone: form.phone.trim(),
        city: form.city.trim(),
        state: form.state.trim(),
        address: form.address.trim(),
        mission: form.mission.trim(),
      });

      updateUser({
        contactPerson: updated.contactPerson ?? form.contactPerson,
        name: updated.contactPerson ?? form.contactPerson,
        phone: updated.phone ?? form.phone,
        city: updated.city ?? form.city,
        state: updated.state ?? form.state,
        address: updated.address ?? form.address,
        mission: updated.mission ?? form.mission,
      });

      toast.success("Profile saved successfully!");
    } catch (err: any) {
      toast.error(err?.message || "Failed to save profile.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <DashboardShell role="ngo">
      <PageHeader
        title="Organisation Profile"
        subtitle="Manage your NGO details and contact information."
      />
      <form className="grid gap-6 lg:grid-cols-2" onSubmit={handleSubmit}>
        <SectionCard title="Organisation Details">
          <div className="space-y-4">
            <div>
              <Label htmlFor="org-name">Organisation Name</Label>
              <Input
                id="org-name"
                className="mt-1"
                value={form.orgName}
                disabled
                title="Organisation Name cannot be changed after registration."
              />
              <p className="mt-1 text-xs text-muted-foreground">Name cannot be changed.</p>
            </div>
            <div>
              <Label htmlFor="org-reg">Registration Number</Label>
              <Input
                id="org-reg"
                className="mt-1"
                value={form.registrationNumber}
                disabled
                title="Registration number cannot be changed."
              />
              <p className="mt-1 text-xs text-muted-foreground">Registration number cannot be changed.</p>
            </div>
            <div>
              <Label htmlFor="org-mission">Mission Statement</Label>
              <Textarea
                id="org-mission"
                className="mt-1 min-h-[100px]"
                value={form.mission}
                onChange={handleChange("mission")}
                placeholder="What is your organisation's core mission?"
              />
            </div>
          </div>
        </SectionCard>

        <SectionCard title="Contact & Location">
          <div className="space-y-4">
            <div>
              <Label htmlFor="org-contact">Contact Person</Label>
              <Input
                id="org-contact"
                className="mt-1"
                value={form.contactPerson}
                onChange={handleChange("contactPerson")}
                placeholder="Name of contact person"
                required
              />
            </div>
            <div>
              <Label htmlFor="org-email">Email Address</Label>
              <Input
                id="org-email"
                type="email"
                className="mt-1"
                value={form.email}
                disabled
                title="Email cannot be changed."
              />
              <p className="mt-1 text-xs text-muted-foreground">Email cannot be changed.</p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="org-phone">Phone Number</Label>
                <Input
                  id="org-phone"
                  className="mt-1"
                  value={form.phone}
                  onChange={handleChange("phone")}
                  placeholder="Contact phone number"
                />
              </div>
              <div>
                <Label htmlFor="org-city">City</Label>
                <Input
                  id="org-city"
                  className="mt-1"
                  value={form.city}
                  onChange={handleChange("city")}
                  placeholder="City"
                />
              </div>
            </div>
            <div>
              <Label htmlFor="org-state">State</Label>
              <Input
                id="org-state"
                className="mt-1"
                value={form.state}
                onChange={handleChange("state")}
                placeholder="State"
              />
            </div>
            <div>
              <Label htmlFor="org-address">Physical Address</Label>
              <Textarea
                id="org-address"
                className="mt-1 min-h-[80px]"
                value={form.address}
                onChange={handleChange("address")}
                placeholder="Office or facility address"
              />
            </div>
          </div>
        </SectionCard>

        <div className="lg:col-span-2">
          <Button type="submit" disabled={saving}>
            {saving ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Saving...
              </span>
            ) : (
              "Save changes"
            )}
          </Button>
        </div>
      </form>
    </DashboardShell>
  );
}

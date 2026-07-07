import { createFileRoute } from "@tanstack/react-router";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, SectionCard } from "@/components/shared/ui";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useApp } from "@/context/AppContext";
import { toast } from "sonner";

export const Route = createFileRoute("/donor/profile")({
  head: () => ({ meta: [{ title: "Profile & Settings — Donate" }] }),
  component: Profile,
});

function Profile() {
  const { user } = useApp();
  const channels = [
    "Email notifications",
    "SMS notifications",
    "WhatsApp notifications",
    "In-app notifications",
  ];
  return (
    <DashboardShell role="donor">
      <PageHeader title="Profile & Settings" subtitle="Manage your account and preferences." />
      <form
        className="grid gap-6 lg:grid-cols-2"
        onSubmit={(e) => {
          e.preventDefault();
          toast.success("Profile saved");
        }}
      >
        <SectionCard title="Personal Information">
          <div className="space-y-4">
            <div>
              <Label>Name</Label>
              <Input className="mt-1" defaultValue={user?.name} />
            </div>
            <div>
              <Label>Email</Label>
              <Input type="email" className="mt-1" defaultValue={user?.email} />
            </div>
            <div>
              <Label>Phone</Label>
              <Input className="mt-1" defaultValue="+91 98765 43210" />
            </div>
            <div>
              <Label>Saved pickup address</Label>
              <Input className="mt-1" defaultValue="42 MG Road, Bengaluru 560001" />
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
        <div className="lg:col-span-2">
          <Button type="submit">Save changes</Button>
        </div>
      </form>
    </DashboardShell>
  );
}

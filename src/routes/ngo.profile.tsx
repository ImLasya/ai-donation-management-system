import { createFileRoute } from "@tanstack/react-router";
import { DashboardShell } from "@/components/portal/DashboardShell";
import { PageHeader, SectionCard, StatusBadge } from "@/components/shared/ui";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

export const Route = createFileRoute("/ngo/profile")({
  head: () => ({ meta: [{ title: "NGO Profile — Donate" }] }),
  component: NGOProfile,
});

function NGOProfile() {
  return (
    <DashboardShell role="ngo">
      <PageHeader
        title="Organisation Profile"
        subtitle="Manage your NGO details and verification."
        action={<StatusBadge status="Fulfilled" />}
      />
      <form
        className="grid gap-6 lg:grid-cols-2"
        onSubmit={(e) => {
          e.preventDefault();
          toast.success("Profile saved");
        }}
      >
        <SectionCard title="Organisation Details">
          <div className="space-y-4">
            <div>
              <Label>Name</Label>
              <Input className="mt-1" defaultValue="Hope Foundation" />
            </div>
            <div>
              <Label>Registration number</Label>
              <Input className="mt-1" defaultValue="KA/2015/0012345" />
            </div>
            <div>
              <Label>Mission</Label>
              <Textarea className="mt-1" defaultValue="Empowering children through education." />
            </div>
            <div>
              <Label>Service radius (km)</Label>
              <Input type="number" className="mt-1" defaultValue={25} />
            </div>
          </div>
        </SectionCard>
        <SectionCard title="Contact">
          <div className="space-y-4">
            <div>
              <Label>Email</Label>
              <Input className="mt-1" defaultValue="contact@hopefoundation.org" />
            </div>
            <div>
              <Label>Phone</Label>
              <Input className="mt-1" defaultValue="+91 80 4000 1234" />
            </div>
            <div>
              <Label>Website</Label>
              <Input className="mt-1" defaultValue="https://hopefoundation.org" />
            </div>
            <div>
              <Label>Address</Label>
              <Textarea className="mt-1" defaultValue="12 Residency Road, Bengaluru 560025" />
            </div>
          </div>
        </SectionCard>
        <div className="lg:col-span-2">
          <Button type="submit">Save changes</Button>
        </div>
      </form>
    </DashboardShell>
  );
}

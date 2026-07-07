import { createFileRoute } from "@tanstack/react-router";
import { PublicLayout } from "@/components/portal/PublicLayout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Mail, Phone, MapPin } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/contact")({
  head: () => ({
    meta: [
      { title: "Contact — Donate" },
      { name: "description", content: "Get in touch with the Donate team." },
    ],
  }),
  component: Contact,
});

function Contact() {
  return (
    <PublicLayout>
      <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:px-8">
        <h1 className="text-4xl font-bold text-foreground">Contact Us</h1>
        <div className="mt-10 grid gap-8 md:grid-cols-2">
          <div className="space-y-4">
            {[
              { icon: Mail, label: "Email", value: "hello@donate.org" },
              { icon: Phone, label: "Phone", value: "+91 80 4000 1234" },
              { icon: MapPin, label: "Office", value: "Koramangala, Bengaluru, India" },
            ].map((c) => (
              <Card key={c.label} className="flex items-center gap-4 p-5">
                <div className="grid h-10 w-10 place-items-center rounded-lg bg-primary/10 text-primary">
                  <c.icon className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">{c.label}</p>
                  <p className="font-medium text-foreground">{c.value}</p>
                </div>
              </Card>
            ))}
          </div>
          <Card className="p-6">
            <form
              className="space-y-4"
              onSubmit={(e) => {
                e.preventDefault();
                toast.success("Message sent! We'll be in touch.");
                (e.target as HTMLFormElement).reset();
              }}
            >
              <div>
                <Label htmlFor="name">Name</Label>
                <Input id="name" required className="mt-1" />
              </div>
              <div>
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" required className="mt-1" />
              </div>
              <div>
                <Label htmlFor="msg">Message</Label>
                <Textarea id="msg" required rows={4} className="mt-1" />
              </div>
              <Button type="submit" className="w-full">
                Send message
              </Button>
            </form>
          </Card>
        </div>
      </div>
    </PublicLayout>
  );
}

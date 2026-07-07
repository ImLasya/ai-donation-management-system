import { useState, type ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { HeartHandshake, Menu, X, Github, Twitter, Linkedin } from "lucide-react";
import { Button } from "@/components/ui/button";

const LINKS = [
  { label: "Home", to: "/" },
  { label: "How It Works", to: "/how-it-works" },
  { label: "Find NGOs", to: "/find-ngos" },
  { label: "About", to: "/about" },
  { label: "FAQ", to: "/faq" },
  { label: "Contact", to: "/contact" },
];

export function PublicLayout({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="sticky top-0 z-30 border-b border-border bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link to="/" className="flex items-center gap-2">
            <div className="grid h-9 w-9 place-items-center rounded-lg bg-primary text-primary-foreground">
              <HeartHandshake className="h-5 w-5" />
            </div>
            <span className="text-lg font-bold text-foreground">Donate</span>
          </Link>
          <nav className="hidden items-center gap-1 md:flex">
            {LINKS.map((l) => (
              <Link
                key={l.to}
                to={l.to}
                className="rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
                activeProps={{ className: "text-foreground" }}
                activeOptions={{ exact: l.to === "/" }}
              >
                {l.label}
              </Link>
            ))}
          </nav>
          <div className="hidden items-center gap-2 md:flex">
            <Button asChild variant="ghost" size="sm">
              <Link to="/login">Sign in</Link>
            </Button>
            <Button asChild size="sm">
              <Link to="/login?redirect=/donor/donate">Donate Items</Link>
            </Button>
          </div>
          <button className="md:hidden" aria-label="Menu" onClick={() => setOpen((o) => !o)}>
            {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
        {open && (
          <div className="border-t border-border bg-background md:hidden">
            <div className="space-y-1 px-4 py-3">
              {LINKS.map((l) => (
                <Link
                  key={l.to}
                  to={l.to}
                  onClick={() => setOpen(false)}
                  className="block rounded-md px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-muted"
                >
                  {l.label}
                </Link>
              ))}
              <div className="flex gap-2 pt-2">
                <Button asChild variant="outline" size="sm" className="flex-1">
                  <Link to="/login">Sign in</Link>
                </Button>
                <Button asChild size="sm" className="flex-1">
                  <Link to="/login?redirect=/donor/donate">Donate</Link>
                </Button>
              </div>
            </div>
          </div>
        )}
      </header>
      <main className="flex-1">{children}</main>
      <footer className="border-t border-border bg-card">
        <div className="mx-auto grid max-w-7xl gap-8 px-4 py-12 sm:px-6 md:grid-cols-4 lg:px-8">
          <div>
            <div className="flex items-center gap-2">
              <div className="grid h-8 w-8 place-items-center rounded-lg bg-primary text-primary-foreground">
                <HeartHandshake className="h-4 w-4" />
              </div>
              <span className="font-bold text-foreground">Donate</span>
            </div>
            <p className="mt-3 text-sm text-muted-foreground">
              AI-powered donation matching for smarter, faster, and more transparent giving.
            </p>
          </div>
          <FooterCol
            title="Platform"
            links={[
              ["How It Works", "/how-it-works"],
              ["Find NGOs", "/find-ngos"],
              ["Donate Items", "/donor/donate"],
              ["Impact", "/about"],
            ]}
          />
          <FooterCol
            title="Organisation"
            links={[
              ["About", "/about"],
              ["Contact", "/contact"],
              ["FAQ", "/faq"],
              ["Register NGO", "/register"],
            ]}
          />
          <div>
            <h4 className="text-sm font-semibold text-foreground">Follow</h4>
            <div className="mt-3 flex gap-3 text-muted-foreground">
              <Twitter className="h-5 w-5" />
              <Linkedin className="h-5 w-5" />
              <Github className="h-5 w-5" />
            </div>
          </div>
        </div>
        <div className="border-t border-border py-4 text-center text-xs text-muted-foreground">
          © 2026 Donate — Intelligent Resource Matching & Distribution.
        </div>
      </footer>
    </div>
  );
}

function FooterCol({ title, links }: { title: string; links: [string, string][] }) {
  return (
    <div>
      <h4 className="text-sm font-semibold text-foreground">{title}</h4>
      <ul className="mt-3 space-y-2">
        {links.map(([label, to]) => (
          <li key={label}>
            <Link to={to} className="text-sm text-muted-foreground hover:text-foreground">
              {label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

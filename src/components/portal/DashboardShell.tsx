import { useState, type ReactNode } from "react";
import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import { Menu, X, LogOut, Bell, HeartHandshake } from "lucide-react";
import { NAV, ROLE_LABEL } from "./nav-config";
import { useApp } from "@/context/AppContext";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Role } from "@/types";

export function DashboardShell({ role, children }: { role: Role; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const { user, logout, notifications } = useApp();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const unread = notifications.filter((n) => !n.read).length;
  const items = NAV[role];

  const handleLogout = () => {
    logout();
    navigate({ to: "/login" });
  };

  const SidebarContent = (
    <div className="flex h-full flex-col">
      <Link to="/" className="flex items-center gap-2 px-5 py-5">
        <div className="grid h-9 w-9 place-items-center rounded-lg bg-primary text-primary-foreground">
          <HeartHandshake className="h-5 w-5" />
        </div>
        <div className="leading-tight">
          <p className="text-sm font-bold text-sidebar-foreground">Donate</p>
          <p className="text-xs text-muted-foreground">{ROLE_LABEL[role]}</p>
        </div>
      </Link>
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-2">
        {items.map((it) => {
          const active =
            pathname === it.to || (it.to !== `/${role}/dashboard` && pathname.startsWith(it.to));
          return (
            <Link
              key={it.to}
              to={it.to}
              onClick={() => setOpen(false)}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-sidebar-primary text-sidebar-primary-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
              )}
            >
              <it.icon className="h-4 w-4 shrink-0" />
              <span className="truncate">{it.label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-sidebar-border p-3">
        <Button variant="ghost" className="w-full justify-start gap-3" onClick={handleLogout}>
          <LogOut className="h-4 w-4" /> Sign out
        </Button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen w-full bg-background">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-sidebar-border bg-sidebar lg:block">
        {SidebarContent}
      </aside>

      {/* Mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-foreground/40" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-64 bg-sidebar shadow-xl">
            <button
              aria-label="Close menu"
              className="absolute right-3 top-4 text-muted-foreground"
              onClick={() => setOpen(false)}
            >
              <X className="h-5 w-5" />
            </button>
            {SidebarContent}
          </aside>
        </div>
      )}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-3 border-b border-border bg-card/80 px-4 backdrop-blur sm:px-6">
          <button aria-label="Open menu" className="lg:hidden" onClick={() => setOpen(true)}>
            <Menu className="h-6 w-6 text-foreground" />
          </button>
          <div className="hidden items-center gap-2 text-sm text-muted-foreground sm:flex">
            <span>Signed in as</span>
            <span className="font-medium text-foreground">{user?.name ?? "Guest"}</span>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to={`/${role}/notifications` as string}
              className="relative grid h-9 w-9 place-items-center rounded-lg hover:bg-muted"
            >
              <Bell className="h-5 w-5 text-foreground" />
              {unread > 0 && (
                <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-destructive" />
              )}
            </Link>
            <div className="grid h-9 w-9 place-items-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
              {(user?.name ?? "?").charAt(0)}
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}

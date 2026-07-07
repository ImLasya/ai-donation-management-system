import {
  LayoutDashboard,
  Camera,
  ScanSearch,
  ListChecks,
  Sparkles,
  Package,
  CalendarClock,
  Truck,
  History,
  Bell,
  Award,
  User,
  Boxes,
  HeartHandshake,
  Building2,
  ClipboardList,
  Users,
  ShieldCheck,
  Activity,
  BarChart3,
  PlusCircle,
} from "lucide-react";
import type { Role } from "@/types";

export interface NavItem {
  label: string;
  to: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  icon: any;
}

export const NAV: Record<Role, NavItem[]> = {
  donor: [
    { label: "Dashboard", to: "/donor/dashboard", icon: LayoutDashboard },
    { label: "Donate Items", to: "/donor/donate", icon: Camera },
    { label: "Detections", to: "/donor/detections", icon: ScanSearch },
    { label: "Review Items", to: "/donor/review", icon: ListChecks },
    { label: "NGO Matches", to: "/donor/matches", icon: Sparkles },
    { label: "Packaging", to: "/donor/packaging", icon: Package },
    { label: "Schedule Pickup", to: "/donor/schedule", icon: CalendarClock },
    { label: "My Donations", to: "/donor/donations", icon: History },
    { label: "Impact", to: "/donor/impact", icon: Award },
    { label: "Notifications", to: "/donor/notifications", icon: Bell },
    { label: "Profile", to: "/donor/profile", icon: User },
  ],
  ngo: [
    { label: "Dashboard", to: "/ngo/dashboard", icon: LayoutDashboard },
    { label: "Demand Registry", to: "/ngo/demands", icon: ClipboardList },
    { label: "Incoming Donations", to: "/ngo/incoming", icon: Truck },
    { label: "Inventory", to: "/ngo/inventory", icon: Boxes },
    { label: "Notifications", to: "/ngo/notifications", icon: Bell },
    { label: "Profile", to: "/ngo/profile", icon: Building2 },
  ],
  admin: [
    { label: "Dashboard", to: "/admin/dashboard", icon: LayoutDashboard },
    { label: "Manage NGOs", to: "/admin/ngos", icon: ShieldCheck },
    { label: "Analytics", to: "/admin/analytics", icon: BarChart3 },
    { label: "System Health", to: "/admin/system-health", icon: Activity },
  ],
};

export const ROLE_LABEL: Record<Role, string> = {
  donor: "Donor Portal",
  ngo: "NGO Portal",
  admin: "Admin Portal",
};
export { HeartHandshake, Users };

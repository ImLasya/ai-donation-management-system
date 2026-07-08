import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type {
  Role,
  User,
  DonationItem,
  DetectionResult,
  AppNotification,
  Demand,
  NGOMatch,
} from "@/types";
import { NOTIFICATIONS, DEMANDS, DETECTIONS } from "@/data/mock";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

interface DonationDraft {
  imageData?: string;
  detections: DetectionResult[];
  items: DonationItem[];
  selectedMatch?: NGOMatch;
  packagingDone: boolean;
  donationId?: number;
}

interface AppState {
  user: User | null;
  login: (role: Role) => void;
  authenticate: (
    email: string,
    password: string,
  ) => Promise<{ success: boolean; error?: string; user?: User }>;
  register: (payload: {
    name: string;
    email: string;
    role: Role;
    password: string;
    org?: string;
    phone?: string;
    city?: string;
    state?: string;
    registrationNumber?: string;
    contactPerson?: string;
    address?: string;
    focusAreas?: string;
    mission?: string;
  }) => Promise<{ success: boolean; error?: string; user?: User }>;
  logout: () => void;
  updateUser: (patch: Partial<User>) => void;
  draft: DonationDraft;
  setDraft: (d: Partial<DonationDraft>) => void;
  resetDraft: () => void;
  notifications: AppNotification[];
  markRead: (id: string) => void;
  markAllRead: () => void;
  removeNotification: (id: string) => void;
  demands: Demand[];
  addDemand: (d: Demand) => void;
  updateDemand: (id: string, patch: Partial<Demand>) => void;
  removeDemand: (id: string) => void;
}

const AppContext = createContext<AppState | null>(null);

const emptyDraft: DonationDraft = { detections: [], items: [], packagingDone: false };

function usePersisted<T>(key: string, initial: T): [T, (v: T | ((p: T) => T)) => void] {
  const [state, setState] = useState<T>(() => {
    if (typeof window === "undefined") return initial;
    try {
      const raw = localStorage.getItem(key);
      return raw ? (JSON.parse(raw) as T) : initial;
    } catch {
      return initial;
    }
  });
  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(state));
    } catch {
      /* ignore */
    }
  }, [key, state]);
  return [state, setState];
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = usePersisted<User | null>("da_user", null);
  const [token, setToken] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("da_token");
  });

  const [draft, setDraftState] = usePersisted<DonationDraft>("da_draft", emptyDraft);
  const [notifications, setNotifications] = usePersisted<AppNotification[]>("da_notif", []);
  const [demands, setDemands] = usePersisted<Demand[]>("da_demands", DEMANDS);

  // Poll real backend notifications if logged in
  useEffect(() => {
    if (!token) {
      setNotifications([]);
      return;
    }

    let active = true;
    const fetchNotifications = async () => {
      try {
        const res = await fetch(`${BASE_URL}/api/donations/notifications/list`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        if (res.ok && active) {
          const data = await res.json();
          setNotifications(
            data.map((n: any) => ({
              id: String(n.id),
              title: n.title,
              message: n.message,
              read: n.isRead,
              timestamp: n.createdAt,
              type: n.type,
              relatedRequestId: n.relatedRequestId,
            })),
          );
        }
      } catch (err) {
        console.error("Failed to fetch notifications:", err);
      }
    };

    fetchNotifications();
    const interval = setInterval(fetchNotifications, 8000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [token]);

  // Sync token to localStorage
  useEffect(() => {
    if (token) {
      localStorage.setItem("da_token", token);
    } else {
      localStorage.removeItem("da_token");
    }
  }, [token]);

  // Load user profile on mount if token exists
  useEffect(() => {
    if (!token) {
      setUser(null);
      return;
    }

    let active = true;
    const fetchMe = async () => {
      try {
        const res = await fetch(`${BASE_URL}/api/auth/me`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        if (res.ok) {
          const data = await res.json();
          if (active) {
            setUser({
              id: String(data.id),
              name: data.name,
              email: data.email,
              role: data.role.toLowerCase() as Role,
              org: data.org,
              phone: data.phone,
              city: data.city,
              state: data.state,
              registrationNumber: data.registrationNumber,
              contactPerson: data.contactPerson,
              address: data.address,
              focusAreas: data.focusAreas,
              mission: data.mission,
            });
          }
        } else {
          if (active) {
            setToken(null);
            setUser(null);
          }
        }
      } catch (err) {
        console.error("Failed to load user session", err);
      }
    };

    fetchMe();
    return () => {
      active = false;
    };
  }, [token]);

  const value: AppState = {
    user,
    login: (role) => {
      if (role === "donor") {
        setUser({ id: "u_donor", name: "Aarav Sharma", email: "aarav@example.com", role: "donor" });
      } else if (role === "ngo") {
        setUser({
          id: "u_ngo",
          name: "Priya Nair",
          email: "priya@hopefoundation.org",
          role: "ngo",
          org: "Hope Foundation",
        });
      } else if (role === "admin") {
        setUser({
          id: "u_admin",
          name: "System Admin",
          email: "admin@donateai.org",
          role: "admin",
        });
      }
    },
    authenticate: async (email, password) => {
      try {
        const res = await fetch(`${BASE_URL}/api/auth/login`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ email, password }),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          return {
            success: false,
            error: errData.detail || "We couldn't sign you in with those credentials.",
          };
        }

        const data = await res.json();
        const loggedUser: User = {
          id: String(data.user.id),
          name: data.user.name,
          email: data.user.email,
          role: data.user.role.toLowerCase() as Role,
          org: data.user.org,
          phone: data.user.phone,
          city: data.user.city,
          state: data.user.state,
          registrationNumber: data.user.registrationNumber,
          contactPerson: data.user.contactPerson,
          address: data.user.address,
          focusAreas: data.user.focusAreas,
          mission: data.user.mission,
        };

        setToken(data.access_token);
        setUser(loggedUser);
        return { success: true, user: loggedUser };
      } catch (err) {
        return {
          success: false,
          error: "Unable to connect to the server. Please check if backend is running.",
        };
      }
    },
    register: async (payload) => {
      const isDonor = payload.role === "donor";
      const endpoint = isDonor ? "/api/auth/register/donor" : "/api/auth/register/ngo";

      const body = isDonor
        ? {
            email: payload.email,
            password: payload.password,
            name: payload.name,
            phone: payload.phone,
            city: payload.city,
            state: payload.state,
          }
        : {
            email: payload.email,
            password: payload.password,
            org: payload.org,
            registrationNumber: payload.registrationNumber,
            contactPerson: payload.contactPerson,
            phone: payload.phone,
            address: payload.address,
            city: payload.city,
            state: payload.state,
            focusAreas: payload.focusAreas,
            mission: payload.mission,
          };

      try {
        const res = await fetch(`${BASE_URL}${endpoint}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(body),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          return { success: false, error: errData.detail || "Registration failed." };
        }

        return { success: true };
      } catch (err) {
        return {
          success: false,
          error: "Unable to connect to the server. Please check if backend is running.",
        };
      }
    },
    logout: () => {
      setToken(null);
      setUser(null);
      localStorage.removeItem("da_token");
      localStorage.removeItem("da_user");
    },
    updateUser: (patch) => {
      setUser((prev) => prev ? { ...prev, ...patch } : prev);
    },
    draft,
    setDraft: (d) => setDraftState((p) => ({ ...p, ...d })),
    resetDraft: () => setDraftState(emptyDraft),
    notifications,
    markRead: async (id) => {
      setNotifications((p) => p.map((n) => (n.id === id ? { ...n, read: true } : n)));
      if (!token) return;
      try {
        await fetch(`${BASE_URL}/api/donations/notifications/read/${id}`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
      } catch (err) {
        console.error("Failed to mark notification read in backend", err);
      }
    },
    markAllRead: async () => {
      setNotifications((p) => p.map((n) => ({ ...n, read: true })));
      if (!token) return;
      const unreadIds = notifications.filter((n) => !n.read).map((n) => n.id);
      for (const id of unreadIds) {
        try {
          await fetch(`${BASE_URL}/api/donations/notifications/read/${id}`, {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });
        } catch (err) {
          console.error(`Failed to mark notification ${id} read`, err);
        }
      }
    },
    removeNotification: (id) => setNotifications((p) => p.filter((n) => n.id !== id)),
    demands,
    addDemand: (d) => setDemands((p) => [d, ...p]),
    updateDemand: (id, patch) =>
      setDemands((p) => p.map((d) => (d.id === id ? { ...d, ...patch } : d))),
    removeDemand: (id) => setDemands((p) => p.filter((d) => d.id !== id)),
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}

export const seedDetections = DETECTIONS;

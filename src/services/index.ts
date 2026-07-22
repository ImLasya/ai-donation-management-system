// Service abstractions for future FastAPI backend integration.
// All methods honour VITE_ENABLE_MOCK_API and return typed contracts.
export * from "./apiClient";
export * from "./detectionService";

import { NGOS, MATCHES, DONATIONS } from "@/data/mock";
import { MOCK_MODE, apiRequest, delay } from "./apiClient";
import type { NGO, NGOMatch, Donation } from "@/types";

export const ngoService = {
  list: async (): Promise<NGO[]> => (MOCK_MODE ? (await delay(200), NGOS) : apiRequest("/ngos")),
  get: async (id: string): Promise<NGO | undefined> =>
    MOCK_MODE ? (await delay(150), NGOS.find((n) => n.id === id)) : apiRequest(`/ngos/${id}`),
};

export const matchingService = {
  find: async (): Promise<NGOMatch[]> =>
    MOCK_MODE ? (await delay(400), MATCHES) : apiRequest("/matches/find", { method: "POST" }),
  get: async (id: string): Promise<NGOMatch | undefined> =>
    MOCK_MODE ? (await delay(150), MATCHES.find((m) => m.id === id)) : apiRequest(`/matches/${id}`),
};

export interface ImpactSummary {
  totalDonations: number;
  totalItemsDonated: number;
  ngosHelped: number;
  beneficiariesReached: number | null;
  beneficiariesIsEstimated: boolean;
  beneficiariesEstimationMethod?: string | null;
}

export interface MonthlyDonationPoint {
  month: string;
  year: number;
  count: number;
}

export interface CategoryDistributionItem {
  category: string;
  quantity: number;
}

export interface Achievement {
  key: string;
  title: string;
  description: string;
  unlocked: boolean;
  progress: number;
  target: number;
  unlockedAt?: string | null;
}

export interface DonorImpactResponse {
  summary: ImpactSummary;
  monthlyDonations: MonthlyDonationPoint[];
  categoryDistribution: CategoryDistributionItem[];
  achievements: Achievement[];
}

export const donationService = {
  list: async (): Promise<Donation[]> =>
    MOCK_MODE ? (await delay(200), DONATIONS) : apiRequest("/donations/list"),
  get: async (id: string): Promise<Donation | undefined> =>
    MOCK_MODE
      ? (await delay(150), DONATIONS.find((d) => d.id === id))
      : apiRequest(`/donations/${id}`),
  getImpactAnalytics: async (): Promise<DonorImpactResponse> => {
    if (MOCK_MODE) {
      await delay(300);
      return {
        summary: {
          totalDonations: 12,
          totalItemsDonated: 148,
          ngosHelped: 7,
          beneficiariesReached: 444,
          beneficiariesIsEstimated: true,
          beneficiariesEstimationMethod: "total_items_donated * 3",
        },
        monthlyDonations: [
          { month: "Jan", year: 2026, count: 2 },
          { month: "Feb", year: 2026, count: 3 },
          { month: "Mar", year: 2026, count: 1 },
          { month: "Apr", year: 2026, count: 4 },
          { month: "May", year: 2026, count: 2 },
          { month: "Jun", year: 2026, count: 0 },
          { month: "Jul", year: 2026, count: 1 },
        ],
        categoryDistribution: [
          { category: "Books", quantity: 38 },
          { category: "Clothing", quantity: 27 },
          { category: "Food", quantity: 18 },
        ],
        achievements: [
          { key: "FIRST_DONATION", title: "First Donation", description: "Complete your first donation", unlocked: true, progress: 1, target: 1 },
          { key: "STREAK_5_WEEK", title: "5-Week Streak", description: "Donate in 5 consecutive calendar weeks", unlocked: true, progress: 5, target: 5 },
          { key: "HELPED_5_NGOS", title: "5 NGOs Helped", description: "Support 5 or more unique NGOs", unlocked: true, progress: 5, target: 5 },
          { key: "ITEMS_100_MILESTONE", title: "100 Items Milestone", description: "Donate 100 or more items", unlocked: true, progress: 100, target: 100 },
          { key: "BENEFICIARIES_1000", title: "1,000 Beneficiaries", description: "Reach 1,000 or more beneficiaries", unlocked: false, progress: 444, target: 1000 },
        ],
      };
    }

    const data = await apiRequest<any>("/donations/impact");
    return {
      summary: {
        totalDonations: data.summary.total_donations,
        totalItemsDonated: data.summary.total_items_donated,
        ngosHelped: data.summary.ngos_helped,
        beneficiariesReached: data.summary.beneficiaries_reached,
        beneficiariesIsEstimated: data.summary.beneficiaries_is_estimated,
        beneficiariesEstimationMethod: data.summary.beneficiaries_estimation_method,
      },
      monthlyDonations: data.monthly_donations.map((d: any) => ({
        month: d.month,
        year: d.year,
        count: d.count,
      })),
      categoryDistribution: data.category_distribution.map((c: any) => ({
        category: c.category,
        quantity: c.quantity,
      })),
      achievements: data.achievements.map((a: any) => ({
        key: a.key,
        title: a.title,
        description: a.description,
        unlocked: a.unlocked,
        progress: a.progress,
        target: a.target,
        unlockedAt: a.unlocked_at,
      })),
    };
  },
  getDonorDashboardStats: async (): Promise<any> => {
    if (MOCK_MODE) {
      await delay(200);
      return {
        totalDonations: 12,
        activeDonations: 2,
        completedDonations: 10,
        waitingForMatch: 0,
        newMatchesAvailable: 1,
        upcomingPickups: [
          { donationId: "1", date: "2026-07-21", timeSlot: "10:00 AM - 12:00 PM", ngoName: "Save the Children", address: "123 Main St", phone: "555-0199" }
        ],
        recentActivity: [
          { donationId: "1", oldStatus: "NGO_ACCEPTED", newStatus: "PACKAGING_IN_PROGRESS", timestamp: "2026-07-20 12:00", note: "Packaging started." }
        ]
      };
    }
    return apiRequest<any>("/donations/donor/dashboard-stats");
  }
};

export interface ProfileUpdatePayload {
  name?: string;
  phone?: string;
  city?: string;
  state?: string;
  address?: string;
  contactPerson?: string;
  mission?: string;
}

export const userService = {
  getProfile: async () => MOCK_MODE
    ? (await delay(150), null)
    : apiRequest<any>("/auth/me"),

  updateProfile: async (payload: ProfileUpdatePayload) => {
    if (MOCK_MODE) {
      await delay(300);
      return payload;
    }
    return apiRequest<any>("/auth/profile", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },
};

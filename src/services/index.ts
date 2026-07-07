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

export const donationService = {
  list: async (): Promise<Donation[]> =>
    MOCK_MODE ? (await delay(200), DONATIONS) : apiRequest("/donations"),
  get: async (id: string): Promise<Donation | undefined> =>
    MOCK_MODE
      ? (await delay(150), DONATIONS.find((d) => d.id === id))
      : apiRequest(`/donations/${id}`),
};

export type Role = "donor" | "ngo" | "admin";

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  avatar?: string;
  org?: string;
  phone?: string;
  city?: string;
  state?: string;
  registrationNumber?: string;
  contactPerson?: string;
  address?: string;
  focusAreas?: string;
  mission?: string;
}

export type Category =
  | "Clothing"
  | "Food"
  | "Books"
  | "Education"
  | "Electronics"
  | "Furniture"
  | "Kitchen"
  | "Household"
  | "Hygiene"
  | "Toys"
  | "Medical"
  | "Other";

export type Condition =
  "New" | "Like New" | "Good" | "Fair" | "Needs Repair" | "Poor" | "Not Assessed";

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface DetectionResult {
  id: string;
  label: string;
  category: Category;
  quantity: number;
  confidence: number;
  bbox: BoundingBox;
}

export interface DonationItem {
  id: string;
  label: string;
  category: Category;
  quantity: number;
  confidence?: number;
  condition: Condition;
  notes?: string;
}

export type Priority = "Low" | "Medium" | "High" | "Urgent";
export type DemandStatus = "Active" | "Partially Fulfilled" | "Fulfilled" | "Expired" | "Paused";

export interface Demand {
  id: string;
  ngoId: string;
  itemName: string;
  category: Category;
  quantityRequired: number;
  quantityFulfilled: number;
  priority: Priority;
  expiryDate: string;
  description?: string;
  conditionAccepted: Condition[];
  status: DemandStatus;
}

export interface NGO {
  id: string;
  name: string;
  logo?: string;
  verified: boolean;
  city: string;
  state: string;
  distanceKm: number;
  mission: string;
  description: string;
  categories: Category[];
  beneficiaries: number;
  itemsReceived: number;
  activeDemands: number;
  priority: Priority;
}

export interface MatchScoreBreakdown {
  itemTypeMatch: number;
  quantityFit: number;
  proximity: number;
  ngoPriority: number;
}

export interface NGOMatch {
  id: string;
  ngo: NGO;
  overallScore: number;
  breakdown: MatchScoreBreakdown;
  reasons: string[];
  itemsNeeded: string[];
  urgency: Priority;
  demandExpiry: string;
}

export type DonationStatus =
  | "Matched"
  | "Packaging Notified"
  | "Pickup Scheduled"
  | "Collected"
  | "Delivered"
  | "Acknowledged";

export interface TrackingEvent {
  status: DonationStatus;
  timestamp: string;
  description: string;
  done: boolean;
}

export interface Donation {
  id: string;
  items: DonationItem[];
  ngoName: string;
  ngoId: string;
  date: string;
  status: DonationStatus;
  pickupDate?: string;
  beneficiaries: number;
  events: TrackingEvent[];
}

export interface Pickup {
  id: string;
  donationId: string;
  date: string;
  slot: string;
  address: string;
  ngoName: string;
  instructions?: string;
  status: "Scheduled" | "Collected" | "Delivered" | "Cancelled";
}

export type NotificationType =
  | "Match Found"
  | "NGO Accepted"
  | "Packaging Reminder"
  | "Pickup Scheduled"
  | "Pickup Reminder"
  | "Item Collected"
  | "Donation Delivered"
  | "Donation Acknowledged"
  | "Demand Expiring"
  | "New Compatible Donation";

export interface AppNotification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
}

export interface InventoryItem {
  id: string;
  name: string;
  category: Category;
  quantity: number;
  source: string;
  receivedDate: string;
  distributionStatus: "In Stock" | "Allocated" | "Distributed";
}

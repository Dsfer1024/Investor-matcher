export interface Investor {
  id: string;
  rank: number;
  // Scores & tier
  tier: 1 | 2 | 3;
  prestigeScore: number;
  fitScore: number;
  // Fund identity
  fundName: string;
  firmUrl: string | null;
  recommendedPartner: string | null;
  partnerTitle: string | null;
  partnerLinkedIn: string | null;
  // Investment parameters
  geoFocus: string | null;
  typicalLeadCheckUsd: string | null;
  leadsRoundFrequently: string | null;
  // Narrative
  whyFit: string[];
  relevantPastInvestments: string[];
  evidenceLinks: string[];
  // Conflict
  hasCompetitorConflict: boolean;
  conflictingCompetitors: string[];
  // Meta
  notes: string | null;
  source: string;
}

export const BUSINESS_TYPES = [
  "B2B SaaS",
  "Vertical SaaS",
  "Vertical AI",
  "Vertical Fintech",
  "Fintech",
  "Healthcare IT",
] as const;

export type BusinessType = (typeof BUSINESS_TYPES)[number];

export const ROUND_STAGES = [
  "Pre-Seed",
  "Seed",
  "Series A",
  "Series B",
  "Series C+",
] as const;

export type RoundStage = (typeof ROUND_STAGES)[number];

export interface SearchFormData {
  companyUrl: string;
  broadIndustry: string;
  targetCustomer: string;
  arr: string;
  arrGrowth: string;
  businessTypes: BusinessType[];
  roundStage: RoundStage | "";
  furtherContext: string;
  competitors: string[];
  spreadsheetFile: File | null;
}

export interface ProgressStep {
  id: string;
  label: string;
  status: "pending" | "active" | "complete" | "error";
}

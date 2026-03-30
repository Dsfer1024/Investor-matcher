export interface Investor {
  id: string;
  rank: number;
  fitScore: number;
  fundName: string;
  targetPartner: string | null;
  fundSize: string | null;
  checkSize: string | null;
  leadOrFollow: string | null;
  areasOfFocus: string[];
  relevantPortfolioCompanies: string[];
  hasCompetitorConflict: boolean;
  conflictingCompetitors: string[];
  website: string | null;
  linkedinUrl: string | null;
  geography: string | null;
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

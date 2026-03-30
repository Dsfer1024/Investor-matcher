export interface Investor {
  id: string;
  rank: number;
  tier: 1 | 2 | 3;
  prestigeScore: number;
  fitScore: number;
  fundName: string;
  firmUrl: string | null;
  recommendedPartner: string | null;
  partnerTitle: string | null;
  partnerLinkedIn: string | null;
  geoFocus: string | null;
  typicalLeadCheckUsd: string | null;
  leadsRoundFrequently: string | null;
  whyFit: string[];
  relevantPastInvestments: string[];
  evidenceLinks: string[];
  hasCompetitorConflict: boolean;
  conflictingCompetitors: string[];
  notes: string | null;
  source: string;
}

export const KEYWORDS = [
  "B2B SaaS",
  "Vertical SaaS",
  "Vertical AI",
  "Vertical Fintech",
  "Fintech",
  "Healthcare IT",
  "Marketplace",
  "Developer Tools",
  "Infrastructure",
  "Consumer",
] as const;

export type Keyword = (typeof KEYWORDS)[number];

export const ICP_SEGMENTS = ["SMB", "Mid-market", "Enterprise"] as const;
export type IcpSegment = (typeof ICP_SEGMENTS)[number];

export const ROUND_STAGES = [
  "Pre-Seed",
  "Seed",
  "Bridge (Seed-A)",
  "Series A",
  "Bridge (A-B)",
  "Series B",
  "Bridge (B and Beyond)",
  "Series C+",
  "Majority Buyout",
] as const;

export type RoundStage = (typeof ROUND_STAGES)[number];

export const INVESTOR_TYPES = ["VC", "Growth Equity", "Private Equity"] as const;
export type InvestorType = (typeof INVESTOR_TYPES)[number];

export const INDUSTRIES = [
  "Construction Tech",
  "Field Services",
  "Legal Tech",
  "Logistics & Supply Chain",
  "Real Estate Tech",
  "HR Tech",
  "EdTech",
  "Retail Tech",
  "Manufacturing Tech",
  "Insurance Tech",
  "Energy Tech",
  "Government Tech",
  "Agriculture Tech",
  "Healthcare Tech",
  "Financial Services",
  "Media & Entertainment",
  "Travel & Hospitality",
  "Professional Services",
  "Cybersecurity",
  "Climate Tech",
] as const;

export type Industry = string; // string to allow custom entries

export interface SearchFormData {
  companyUrl: string;
  industries: Industry[];
  icpSegments: IcpSegment[];
  arr: string;
  arrGrowth: string;
  raiseAmount: string;
  keywords: Keyword[];
  roundStage: RoundStage | "";
  investorTypes: InvestorType[];
  furtherContext: string;
  competitors: string[];
}

export interface ProgressStep {
  id: string;
  label: string;
  status: "pending" | "active" | "complete" | "error";
}

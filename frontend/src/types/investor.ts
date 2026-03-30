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
  "Series A",
  "Series B",
  "Series C+",
] as const;

export type RoundStage = (typeof ROUND_STAGES)[number];

export interface SearchFormData {
  companyUrl: string;
  broadIndustry: string;
  icpSegments: IcpSegment[];
  arr: string;
  arrGrowth: string;
  keywords: Keyword[];
  roundStage: RoundStage | "";
  furtherContext: string;
  competitors: string[];
}

export interface ProgressStep {
  id: string;
  label: string;
  status: "pending" | "active" | "complete" | "error";
}

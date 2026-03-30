import type { Investor } from "../types/investor";

function escapeCsv(value: string | null | undefined): string {
  if (value == null) return "";
  const str = String(value);
  if (str.includes(",") || str.includes('"') || str.includes("\n")) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

export function exportToCsv(investors: Investor[], filename = "investor-list.csv"): void {
  // Headers match the prompt spec exactly
  const headers = [
    "Tier",
    "PrestigeScore",
    "FitScore",
    "Firm",
    "RecommendedPartner",
    "PartnerTitle",
    "FirmURL",
    "PartnerLinkedIn",
    "GeoFocus",
    "TypicalLeadCheckUSD",
    "LeadsSeriesAFrequently",
    "WhyFit",
    "RelevantPastInvestments",
    "EvidenceLinks",
    "CompetitorConflict",
    "ConflictingCompetitors",
    "Notes",
  ];

  const rows = investors.map((inv) => [
    inv.tier,
    inv.prestigeScore,
    inv.fitScore,
    escapeCsv(inv.fundName),
    escapeCsv(inv.recommendedPartner),
    escapeCsv(inv.partnerTitle),
    escapeCsv(inv.firmUrl),
    escapeCsv(inv.partnerLinkedIn),
    escapeCsv(inv.geoFocus),
    escapeCsv(inv.typicalLeadCheckUsd),
    escapeCsv(inv.leadsRoundFrequently),
    escapeCsv(inv.whyFit.join(" | ")),
    escapeCsv(inv.relevantPastInvestments.join(" | ")),
    escapeCsv(inv.evidenceLinks.join(" | ")),
    inv.hasCompetitorConflict ? "YES" : "",
    escapeCsv(inv.conflictingCompetitors.join("; ")),
    escapeCsv(inv.notes),
  ]);

  const csvContent = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

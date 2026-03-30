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
  const headers = [
    "Rank",
    "Tier",
    "Fit Score",
    "Prestige Score",
    "Fund Name",
    "Target Partner",
    "Partner Title",
    "Fund Size",
    "Check Size",
    "Lead or Follow",
    "Areas of Focus",
    "Why Fit",
    "Evidence Links",
    "Relevant Portfolio Companies",
    "Competitor Conflict",
    "Conflicting Competitors",
    "Website",
    "Geography",
    "Notes",
  ];

  const rows = investors.map((inv) => [
    inv.rank,
    inv.tier,
    inv.fitScore,
    inv.prestigeScore,
    escapeCsv(inv.fundName),
    escapeCsv(inv.targetPartner),
    escapeCsv(inv.partnerTitle),
    escapeCsv(inv.fundSize),
    escapeCsv(inv.checkSize),
    escapeCsv(inv.leadOrFollow),
    escapeCsv(inv.areasOfFocus.join("; ")),
    escapeCsv(inv.whyFit.join("; ")),
    escapeCsv(inv.evidenceLinks.join("; ")),
    escapeCsv(inv.relevantPortfolioCompanies.join("; ")),
    inv.hasCompetitorConflict ? "YES" : "",
    escapeCsv(inv.conflictingCompetitors.join("; ")),
    escapeCsv(inv.website),
    escapeCsv(inv.geography),
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

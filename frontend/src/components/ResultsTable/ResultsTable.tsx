import type { Investor } from "../../types/investor";
import { useTableSort } from "../../hooks/useTableSort";
import { exportToCsv } from "../../utils/csvExport";

interface Props {
  investors: Investor[];
}

function TierBadge({ tier }: { tier: 1 | 2 | 3 }) {
  const styles: Record<number, string> = {
    1: "bg-yellow-100 text-yellow-800 border border-yellow-300",
    2: "bg-gray-100 text-gray-600 border border-gray-300",
    3: "bg-white text-gray-400 border border-gray-200",
  };
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${styles[tier]}`}>
      T{tier}
    </span>
  );
}

function ScorePill({ score }: { score: number }) {
  const color =
    score >= 75 ? "bg-green-100 text-green-800"
    : score >= 50 ? "bg-yellow-100 text-yellow-800"
    : "bg-red-100 text-red-800";
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${color}`}>
      {score}
    </span>
  );
}

function SortIcon({ active, direction }: { active: boolean; direction: "asc" | "desc" }) {
  if (!active) return <span className="text-gray-300 ml-1">⇅</span>;
  return <span className="text-blue-500 ml-1">{direction === "asc" ? "↑" : "↓"}</span>;
}

function Pill({ text }: { text: string }) {
  return (
    <span className="inline-block bg-gray-100 text-gray-600 text-xs px-1.5 py-0.5 rounded mr-1 mb-1">
      {text}
    </span>
  );
}

function WhyFitCell({ bullets }: { bullets: string[] }) {
  if (!bullets?.length) return <span className="text-gray-300 text-xs">—</span>;
  return (
    <ul className="list-disc list-inside space-y-0.5 min-w-[220px] max-w-[280px]">
      {bullets.slice(0, 3).map((b, i) => (
        <li key={i} className="text-xs text-gray-600 leading-snug">{b}</li>
      ))}
    </ul>
  );
}

function EvidenceLinks({ links }: { links: string[] }) {
  if (!links?.length) return <span className="text-gray-300 text-xs">—</span>;
  return (
    <div className="flex gap-1 flex-wrap">
      {links.slice(0, 3).map((url, i) => (
        <a
          key={i}
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block px-1.5 py-0.5 bg-blue-50 text-blue-600 text-xs rounded hover:bg-blue-100 font-mono"
        >
          [{i + 1}]
        </a>
      ))}
    </div>
  );
}

export default function ResultsTable({ investors }: Props) {
  const { sorted, sortKey, direction, toggleSort } = useTableSort(investors);

  const sortableCols = [
    { key: "rank" as const, label: "#" },
    { key: "tier" as const, label: "Tier" },
    { key: "fitScore" as const, label: "FitScore" },
    { key: "prestigeScore" as const, label: "Prestige" },
    { key: "fundName" as const, label: "Firm" },
  ];

  const staticCols = [
    "Recommended Partner",
    "Partner Title",
    "Geo Focus",
    "Lead Check (USD)",
    "Leads Round?",
    "Why Fit",
    "Past Investments",
    "Evidence",
    "Notes",
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold text-gray-800">
          {investors.length} Investors Found
        </h2>
        <button
          onClick={() => exportToCsv(sorted)}
          className="px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-lg hover:bg-gray-50 text-gray-700 transition-colors"
        >
          Export CSV
        </button>
      </div>

      {investors.some((i) => i.hasCompetitorConflict) && (
        <div className="mb-3 flex items-center gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          <span className="w-3 h-3 rounded-sm bg-red-400 flex-shrink-0" />
          Red rows indicate investors who have backed one of your competitors.
        </div>
      )}

      <div className="overflow-x-auto rounded-xl border border-gray-200 shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {sortableCols.map(({ key, label }) => (
                <th
                  key={key}
                  className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wide cursor-pointer hover:text-gray-700 whitespace-nowrap"
                  onClick={() => toggleSort(key)}
                >
                  {label}
                  <SortIcon active={sortKey === key} direction={direction} />
                </th>
              ))}
              {staticCols.map((h) => (
                <th
                  key={h}
                  className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wide whitespace-nowrap"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {sorted.map((inv) => (
              <tr
                key={inv.id}
                className={
                  inv.hasCompetitorConflict
                    ? "bg-red-50 border-l-4 border-red-400"
                    : "hover:bg-gray-50"
                }
              >
                {/* # */}
                <td className="px-3 py-3 text-gray-400 text-xs font-mono">{inv.rank}</td>

                {/* Tier */}
                <td className="px-3 py-3">
                  <TierBadge tier={inv.tier} />
                </td>

                {/* FitScore */}
                <td className="px-3 py-3">
                  <ScorePill score={inv.fitScore} />
                </td>

                {/* PrestigeScore */}
                <td className="px-3 py-3">
                  <ScorePill score={inv.prestigeScore} />
                </td>

                {/* Firm */}
                <td className="px-3 py-3 font-medium text-gray-800 whitespace-nowrap">
                  {inv.firmUrl ? (
                    <a
                      href={inv.firmUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:text-blue-600 hover:underline"
                    >
                      {inv.fundName}
                    </a>
                  ) : (
                    inv.fundName
                  )}
                  {inv.hasCompetitorConflict && (
                    <span className="ml-2 text-xs text-red-600 font-normal">
                      ⚠ Conflict: {inv.conflictingCompetitors.join(", ")}
                    </span>
                  )}
                </td>

                {/* Recommended Partner */}
                <td className="px-3 py-3 text-gray-600 whitespace-nowrap">
                  {inv.recommendedPartner ? (
                    inv.partnerLinkedIn ? (
                      <a
                        href={inv.partnerLinkedIn}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        {inv.recommendedPartner}
                      </a>
                    ) : (
                      inv.recommendedPartner
                    )
                  ) : (
                    <span className="text-gray-300">—</span>
                  )}
                </td>

                {/* Partner Title */}
                <td className="px-3 py-3 text-gray-500 text-xs whitespace-nowrap">
                  {inv.partnerTitle ?? <span className="text-gray-300">—</span>}
                </td>

                {/* Geo Focus */}
                <td className="px-3 py-3 text-gray-600 whitespace-nowrap">
                  {inv.geoFocus ?? <span className="text-gray-300">—</span>}
                </td>

                {/* Lead Check USD */}
                <td className="px-3 py-3 text-gray-600 whitespace-nowrap">
                  {inv.typicalLeadCheckUsd ?? <span className="text-gray-300">—</span>}
                </td>

                {/* Leads Round Frequently */}
                <td className="px-3 py-3 text-center">
                  {inv.leadsRoundFrequently === "Yes" ? (
                    <span className="inline-block px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full font-medium">Yes</span>
                  ) : inv.leadsRoundFrequently === "No" ? (
                    <span className="inline-block px-2 py-0.5 bg-gray-100 text-gray-500 text-xs rounded-full">No</span>
                  ) : (
                    <span className="text-gray-300 text-xs">—</span>
                  )}
                </td>

                {/* Why Fit */}
                <td className="px-3 py-3">
                  <WhyFitCell bullets={inv.whyFit} />
                </td>

                {/* Relevant Past Investments */}
                <td className="px-3 py-3 max-w-[200px]">
                  {inv.relevantPastInvestments?.length > 0 ? (
                    <div className="flex flex-wrap">
                      {inv.relevantPastInvestments.slice(0, 3).map((c) => (
                        <Pill key={c} text={c} />
                      ))}
                      {inv.relevantPastInvestments.length > 3 && (
                        <span className="text-xs text-gray-400">
                          +{inv.relevantPastInvestments.length - 3} more
                        </span>
                      )}
                    </div>
                  ) : (
                    <span className="text-gray-300 text-xs">—</span>
                  )}
                </td>

                {/* Evidence */}
                <td className="px-3 py-3">
                  <EvidenceLinks links={inv.evidenceLinks} />
                </td>

                {/* Notes */}
                <td className="px-3 py-3 text-xs text-gray-500 max-w-[180px]">
                  {inv.notes ?? <span className="text-gray-300">—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

import type { Investor } from "../../types/investor";
import { useTableSort } from "../../hooks/useTableSort";
import { exportToCsv } from "../../utils/csvExport";

interface Props {
  investors: Investor[];
}

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 75
      ? "bg-green-100 text-green-800"
      : score >= 50
      ? "bg-yellow-100 text-yellow-800"
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

export default function ResultsTable({ investors }: Props) {
  const { sorted, sortKey, direction, toggleSort } = useTableSort(investors);

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
              {(
                [
                  { key: "rank", label: "#" },
                  { key: "fitScore", label: "Fit Score" },
                  { key: "fundName", label: "Fund" },
                ] as const
              ).map(({ key, label }) => (
                <th
                  key={key}
                  className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wide cursor-pointer hover:text-gray-700 whitespace-nowrap"
                  onClick={() => toggleSort(key)}
                >
                  {label}
                  <SortIcon active={sortKey === key} direction={direction} />
                </th>
              ))}
              {[
                "Target Partner",
                "Fund Size",
                "Check Size",
                "Lead/Follow",
                "Focus Areas",
                "Relevant Portfolio",
              ].map((h) => (
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
                <td className="px-3 py-3 text-gray-400 text-xs font-mono">{inv.rank}</td>
                <td className="px-3 py-3">
                  <ScoreBadge score={inv.fitScore} />
                </td>
                <td className="px-3 py-3 font-medium text-gray-800 whitespace-nowrap">
                  {inv.website ? (
                    <a
                      href={inv.website}
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
                <td className="px-3 py-3 text-gray-600 whitespace-nowrap">
                  {inv.targetPartner ? (
                    inv.linkedinUrl ? (
                      <a
                        href={inv.linkedinUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        {inv.targetPartner}
                      </a>
                    ) : (
                      inv.targetPartner
                    )
                  ) : (
                    <span className="text-gray-300">—</span>
                  )}
                </td>
                <td className="px-3 py-3 text-gray-600 whitespace-nowrap">
                  {inv.fundSize ?? <span className="text-gray-300">—</span>}
                </td>
                <td className="px-3 py-3 text-gray-600 whitespace-nowrap">
                  {inv.checkSize ?? <span className="text-gray-300">—</span>}
                </td>
                <td className="px-3 py-3 text-gray-600 whitespace-nowrap">
                  {inv.leadOrFollow ?? <span className="text-gray-300">—</span>}
                </td>
                <td className="px-3 py-3 max-w-[200px]">
                  <div className="flex flex-wrap">
                    {inv.areasOfFocus.slice(0, 4).map((f) => (
                      <Pill key={f} text={f} />
                    ))}
                    {inv.areasOfFocus.length > 4 && (
                      <span className="text-xs text-gray-400">
                        +{inv.areasOfFocus.length - 4} more
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-3 py-3 max-w-[200px]">
                  {inv.relevantPortfolioCompanies.length > 0 ? (
                    <div className="flex flex-wrap">
                      {inv.relevantPortfolioCompanies.slice(0, 3).map((c) => (
                        <Pill key={c} text={c} />
                      ))}
                      {inv.relevantPortfolioCompanies.length > 3 && (
                        <span className="text-xs text-gray-400">
                          +{inv.relevantPortfolioCompanies.length - 3} more
                        </span>
                      )}
                    </div>
                  ) : (
                    <span className="text-gray-300 text-xs">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

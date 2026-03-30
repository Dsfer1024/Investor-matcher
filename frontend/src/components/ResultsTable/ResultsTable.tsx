import type { Investor } from "../../types/investor";
import { useTableSort } from "../../hooks/useTableSort";
import { exportToCsv } from "../../utils/csvExport";

interface Props {
  investors: Investor[];
}

function TierBadge({ tier }: { tier: 1 | 2 | 3 }) {
  const styles = {
    1: "bg-yellow-100 text-yellow-800 border border-yellow-300",
    2: "bg-gray-100 text-gray-600 border border-gray-300",
    3: "bg-white text-gray-400 border border-gray-200",
  };
  const labels = { 1: "Tier 1", 2: "Tier 2", 3: "Tier 3" };
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${styles[tier]}`}
    >
      {labels[tier]}
    </span>
  );
}

function ScoreBadge({ score, label }: { score: number; label?: string }) {
  const color =
    score >= 75
      ? "bg-green-100 text-green-800"
      : score >= 50
      ? "bg-yellow-100 text-yellow-800"
      : "bg-red-100 text-red-800";
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${color}`}>
      {label ? `${label}: ` : ""}{score}
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
  if (!bullets || bullets.length === 0) return <span className="text-gray-300 text-xs">—</span>;
  return (
    <ul className="list-disc list-inside space-y-0.5 max-w-[250px]">
      {bullets.slice(0, 3).map((b, i) => (
        <li key={i} className="text-xs text-gray-600 leading-snug">
          {b}
        </li>
      ))}
    </ul>
  );
}

function EvidenceLinks({ links }: { links: string[] }) {
  if (!links || links.length === 0) return <span className="text-gray-300 text-xs">—</span>;
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
                  { key: "tier", label: "Tier" },
                  { key: "fitScore", label: "Fit" },
                  { key: "prestigeScore", label: "Prestige" },
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
                "Partner",
                "Check Size",
                "Lead/Follow",
                "Why Fit",
                "Evidence",
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
                  <TierBadge tier={inv.tier} />
                </td>
                <td className="px-3 py-3">
                  <ScoreBadge score={inv.fitScore} />
                </td>
                <td className="px-3 py-3">
                  <ScoreBadge score={inv.prestigeScore} />
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
                  {inv.notes && (
                    <p className="text-xs text-gray-400 font-normal mt-0.5">{inv.notes}</p>
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
                  {inv.partnerTitle && (
                    <p className="text-xs text-gray-400">{inv.partnerTitle}</p>
                  )}
                </td>
                <td className="px-3 py-3 text-gray-600 whitespace-nowrap">
                  {inv.checkSize ?? <span className="text-gray-300">—</span>}
                </td>
                <td className="px-3 py-3 text-gray-600 whitespace-nowrap">
                  {inv.leadOrFollow ?? <span className="text-gray-300">—</span>}
                </td>
                <td className="px-3 py-3">
                  <WhyFitCell bullets={inv.whyFit} />
                </td>
                <td className="px-3 py-3">
                  <EvidenceLinks links={inv.evidenceLinks} />
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

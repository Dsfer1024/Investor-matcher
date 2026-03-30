import { useState, useMemo } from "react";
import type { Investor } from "../../types/investor";
import { exportToCsv } from "../../utils/csvExport";

interface Props {
  investors: Investor[];
  quickThesis: string;
  companyUrl: string;
}

function companyName(url: string): string {
  try {
    const h = new URL(url).hostname.replace(/^www\./, "");
    const name = h.split(".")[0].replace(/-/g, " ");
    return name.charAt(0).toUpperCase() + name.slice(1);
  } catch {
    return "Your Company";
  }
}

function TierBadge({ tier }: { tier: 1 | 2 | 3 }) {
  const s = {
    1: "bg-yellow-100 text-yellow-800 border-yellow-300",
    2: "bg-slate-100 text-slate-600 border-slate-300",
    3: "bg-white text-gray-400 border-gray-200",
  };
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-semibold border ${s[tier]}`}>
      T{tier}
    </span>
  );
}

function ScoreBar({ score, color }: { score: number; color: string }) {
  return (
    <div className="flex items-center gap-2 min-w-[72px]">
      <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs font-mono text-gray-700 w-6 text-right">{score}</span>
    </div>
  );
}

function ExpandedDetail({ inv }: { inv: Investor }) {
  return (
    <tr>
      <td colSpan={8} className="bg-slate-50 border-b border-slate-200 p-0">
        <div className="grid grid-cols-3 divide-x divide-slate-200">
          <div className="px-5 py-4">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Why Fit</p>
            <ul className="space-y-1.5">
              {inv.whyFit.length ? inv.whyFit.map((b, i) => (
                <li key={i} className="text-sm text-slate-700 flex gap-2">
                  <span className="text-blue-400 flex-shrink-0">•</span>{b}
                </li>
              )) : <li className="text-sm text-slate-400">—</li>}
            </ul>
          </div>
          <div className="px-5 py-4">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Portfolio</p>
            <div className="flex flex-wrap gap-1.5">
              {inv.relevantPastInvestments.length ? inv.relevantPastInvestments.map((c, i) => (
                <span key={i} className="px-2 py-0.5 bg-white border border-slate-200 rounded text-xs text-slate-600 shadow-sm">{c}</span>
              )) : <span className="text-sm text-slate-400">—</span>}
            </div>
          </div>
          <div className="px-5 py-4 space-y-2">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Details</p>
            {inv.geoFocus && <p className="text-sm text-slate-600">📍 {inv.geoFocus}</p>}
            {inv.typicalLeadCheckUsd && <p className="text-sm text-slate-600">💰 {inv.typicalLeadCheckUsd}</p>}
            {inv.leadsRoundFrequently && (
              <p className="text-sm">
                🏆 Leads: <span className={inv.leadsRoundFrequently === "Yes" ? "text-green-600 font-medium" : "text-slate-500"}>{inv.leadsRoundFrequently}</span>
              </p>
            )}
            {inv.notes && <p className="text-xs text-slate-500 italic border-t border-slate-200 pt-2 mt-1">{inv.notes}</p>}
            {inv.evidenceLinks.length > 0 && (
              <div className="flex flex-wrap gap-1 border-t border-slate-200 pt-2">
                {inv.evidenceLinks.map((url, i) => (
                  <a key={i} href={url} target="_blank" rel="noopener noreferrer"
                    className="px-2 py-0.5 bg-blue-50 text-blue-600 border border-blue-200 rounded text-xs hover:bg-blue-100 font-mono">
                    [{i + 1}]
                  </a>
                ))}
              </div>
            )}
          </div>
        </div>
      </td>
    </tr>
  );
}

type SortKey = "rank" | "fitScore" | "prestigeScore" | "tier";

export default function ResultsTable({ investors, quickThesis, companyUrl }: Props) {
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState<0 | 1 | 2 | 3>(0);
  const [sortKey, setSortKey] = useState<SortKey>("rank");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const tier1 = investors.filter(i => i.tier === 1).length;
  const tier2 = investors.filter(i => i.tier === 2).length;
  const tier3 = investors.filter(i => i.tier === 3).length;
  const conflicts = investors.filter(i => i.hasCompetitorConflict).length;

  const filtered = useMemo(() => {
    let list = [...investors];
    if (tierFilter) list = list.filter(i => i.tier === tierFilter);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(i =>
        i.fundName.toLowerCase().includes(q) ||
        (i.recommendedPartner?.toLowerCase().includes(q) ?? false)
      );
    }
    list.sort((a, b) => {
      const av = sortKey === "rank" ? a.rank : sortKey === "fitScore" ? a.fitScore : sortKey === "prestigeScore" ? a.prestigeScore : a.tier;
      const bv = sortKey === "rank" ? b.rank : sortKey === "fitScore" ? b.fitScore : sortKey === "prestigeScore" ? b.prestigeScore : b.tier;
      return sortDir === "asc" ? av - bv : bv - av;
    });
    return list;
  }, [investors, tierFilter, search, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir(key === "rank" || key === "tier" ? "asc" : "desc"); }
  }

  function Th({ col, label }: { col: SortKey; label: string }) {
    const active = sortKey === col;
    return (
      <th onClick={() => toggleSort(col)}
        className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide cursor-pointer hover:text-white select-none whitespace-nowrap">
        {label} <span className="opacity-50">{active ? (sortDir === "asc" ? "↑" : "↓") : "⇅"}</span>
      </th>
    );
  }

  return (
    <div className="space-y-5">

      {/* Header */}
      <div className="rounded-2xl bg-gradient-to-r from-slate-900 to-slate-700 text-white px-6 py-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-slate-400 text-xs uppercase tracking-widest mb-0.5">Investor Research</p>
            <h2 className="text-xl font-bold">{companyName(companyUrl)}</h2>
          </div>
          <button onClick={() => exportToCsv(investors)}
            className="flex-shrink-0 px-4 py-2 bg-white/10 hover:bg-white/20 border border-white/20 rounded-xl text-sm font-medium transition-colors">
            ↓ Export CSV
          </button>
        </div>
        <div className="mt-4 flex gap-4 text-sm">
          <span><span className="font-bold text-white">{investors.length}</span> <span className="text-slate-400">Total</span></span>
          <span><span className="font-bold text-yellow-400">{tier1}</span> <span className="text-slate-400">Tier 1</span></span>
          <span><span className="font-bold text-slate-300">{tier2}</span> <span className="text-slate-400">Tier 2</span></span>
          <span><span className="font-bold text-slate-400">{tier3}</span> <span className="text-slate-500">Tier 3</span></span>
          {conflicts > 0 && <span><span className="font-bold text-red-400">{conflicts}</span> <span className="text-slate-400">Conflicts</span></span>}
        </div>
      </div>

      {/* Quick Thesis */}
      {quickThesis && (
        <div className="bg-white border-l-4 border-emerald-500 rounded-xl px-5 py-4 shadow-sm">
          <p className="text-xs font-semibold text-emerald-600 uppercase tracking-wide mb-1">AI Thesis</p>
          <p className="text-slate-700 text-sm leading-relaxed">{quickThesis}</p>
        </div>
      )}

      {/* Filter bar */}
      <div className="flex gap-2 items-center flex-wrap">
        <input type="text" placeholder="Search firm or partner..." value={search}
          onChange={e => setSearch(e.target.value)}
          className="flex-1 min-w-[200px] border border-gray-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
        <div className="flex gap-1.5">
          {([0, 1, 2, 3] as const).map(t => (
            <button key={t} onClick={() => setTierFilter(t)}
              className={`px-3 py-2 rounded-xl text-xs font-semibold border transition-colors ${tierFilter === t ? "bg-slate-800 text-white border-slate-800" : "bg-white text-slate-600 border-gray-200 hover:border-slate-400"}`}>
              {t === 0 ? "All" : `T${t}`}
            </button>
          ))}
        </div>
        <span className="text-sm text-slate-500">{filtered.length} results</span>
      </div>

      {/* Table */}
      <div className="rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-gradient-to-r from-slate-800 to-slate-700">
            <tr>
              <Th col="rank" label="#" />
              <Th col="tier" label="Tier" />
              <Th col="fitScore" label="Fit" />
              <Th col="prestigeScore" label="Prestige" />
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide">Firm</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide">Partner</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide">Check Size</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide">Leads?</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-slate-100">
            {filtered.map(inv => (
              <>
                <tr key={inv.id}
                  onClick={() => setExpandedId(expandedId === inv.id ? null : inv.id)}
                  className={`cursor-pointer transition-colors ${inv.hasCompetitorConflict ? "bg-red-50 hover:bg-red-100 border-l-4 border-l-red-400" : expandedId === inv.id ? "bg-blue-50" : "hover:bg-slate-50"}`}>
                  <td className="px-4 py-3 text-slate-400 font-mono text-xs">{inv.rank}</td>
                  <td className="px-4 py-3"><TierBadge tier={inv.tier} /></td>
                  <td className="px-4 py-3"><ScoreBar score={inv.fitScore} color="bg-blue-500" /></td>
                  <td className="px-4 py-3"><ScoreBar score={inv.prestigeScore} color="bg-purple-400" /></td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <span className="text-slate-300 text-xs">{expandedId === inv.id ? "▼" : "▶"}</span>
                      <div>
                        {inv.firmUrl
                          ? <a href={inv.firmUrl} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()} className="font-semibold text-slate-800 hover:text-blue-600 hover:underline">{inv.fundName}</a>
                          : <span className="font-semibold text-slate-800">{inv.fundName}</span>}
                        {inv.hasCompetitorConflict && (
                          <p className="text-xs text-red-600 mt-0.5">⚠ {inv.conflictingCompetitors.slice(0, 2).join(", ")}</p>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {inv.recommendedPartner ? (
                      <div>
                        {inv.partnerLinkedIn
                          ? <a href={inv.partnerLinkedIn} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()} className="text-blue-600 hover:underline text-sm">{inv.recommendedPartner}</a>
                          : <span className="text-slate-700 text-sm">{inv.recommendedPartner}</span>}
                        {inv.partnerTitle && <p className="text-xs text-slate-400">{inv.partnerTitle}</p>}
                      </div>
                    ) : <span className="text-slate-300 text-xs">—</span>}
                  </td>
                  <td className="px-4 py-3 text-slate-600 whitespace-nowrap">{inv.typicalLeadCheckUsd ?? <span className="text-slate-300">—</span>}</td>
                  <td className="px-4 py-3">
                    {inv.leadsRoundFrequently === "Yes"
                      ? <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full font-medium">Yes</span>
                      : inv.leadsRoundFrequently === "No"
                      ? <span className="px-2 py-0.5 bg-gray-100 text-gray-500 text-xs rounded-full">No</span>
                      : <span className="text-slate-300 text-xs">—</span>}
                  </td>
                </tr>
                {expandedId === inv.id && <ExpandedDetail key={`${inv.id}-detail`} inv={inv} />}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

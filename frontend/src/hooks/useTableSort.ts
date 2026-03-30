import { useState, useMemo } from "react";
import type { Investor } from "../types/investor";

type SortKey = keyof Pick<
  Investor,
  "rank" | "fitScore" | "fundName" | "fundSize" | "checkSize"
>;

type Direction = "asc" | "desc";

export function useTableSort(investors: Investor[]) {
  const [sortKey, setSortKey] = useState<SortKey>("rank");
  const [direction, setDirection] = useState<Direction>("asc");

  const sorted = useMemo(() => {
    return [...investors].sort((a, b) => {
      const av = a[sortKey] ?? "";
      const bv = b[sortKey] ?? "";
      const cmp =
        typeof av === "number" && typeof bv === "number"
          ? av - bv
          : String(av).localeCompare(String(bv));
      return direction === "asc" ? cmp : -cmp;
    });
  }, [investors, sortKey, direction]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setDirection((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setDirection("asc");
    }
  }

  return { sorted, sortKey, direction, toggleSort };
}

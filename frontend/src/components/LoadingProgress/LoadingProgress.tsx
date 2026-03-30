import type { ProgressStep } from "../../types/investor";

const STEPS: { id: string; label: string }[] = [
  { id: "conflicts", label: "Researching competitor conflicts..." },
  { id: "generate", label: "Generating investor longlist with AI..." },
  { id: "enrich", label: "Enriching & scoring investor profiles..." },
  { id: "gap", label: "Checking for gaps (ensuring 80+ results)..." },
  { id: "rank", label: "Ranking & tiering results..." },
];

interface Props {
  steps: ProgressStep[];
}

export default function LoadingProgress({ steps }: Props) {
  const stepMap = Object.fromEntries(steps.map((s) => [s.id, s]));

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <h2 className="text-base font-semibold text-gray-800 mb-4">Finding your investors...</h2>
      <div className="space-y-3">
        {STEPS.map((def) => {
          const step = stepMap[def.id];
          const status = step?.status ?? "pending";
          const label = step?.label ?? def.label;

          return (
            <div key={def.id} className="flex items-center gap-3">
              <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center">
                {status === "complete" && (
                  <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
                {status === "active" && (
                  <svg
                    className="w-5 h-5 text-blue-500 animate-spin"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8v8H4z"
                    />
                  </svg>
                )}
                {status === "pending" && (
                  <div className="w-5 h-5 rounded-full border-2 border-gray-200" />
                )}
                {status === "error" && (
                  <svg className="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
              </div>
              <span
                className={`text-sm ${
                  status === "active"
                    ? "text-blue-700 font-medium"
                    : status === "complete"
                    ? "text-gray-500 line-through"
                    : "text-gray-400"
                }`}
              >
                {label}
              </span>
            </div>
          );
        })}
      </div>
      <p className="text-xs text-gray-400 mt-4">
        AI research typically takes 60–75 seconds
      </p>
    </div>
  );
}

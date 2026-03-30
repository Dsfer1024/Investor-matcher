import type { ProgressStep } from "../../types/investor";

const STEPS: { id: string; label: string }[] = [
  { id: "generate", label: "Generating & scoring investor list with AI..." },
];

interface Props {
  steps: ProgressStep[];
}

export default function LoadingProgress({ steps }: Props) {
  const stepMap = Object.fromEntries(steps.map((s) => [s.id, s]));

  return (
    <div className="bg-white border border-gray-200 rounded-2xl p-8 shadow-sm">
      {/* Logo + title */}
      <div className="flex items-center gap-3 mb-6">
        <div
          style={{ backgroundColor: "#2d00ff" }}
          className="w-2 h-2 rounded-full animate-pulse"
        />
        <h2 className="text-base font-semibold text-gray-900">Finding your investors...</h2>
      </div>

      <div className="space-y-4">
        {STEPS.map((def) => {
          const step = stepMap[def.id];
          const status = step?.status ?? "pending";
          const label = step?.label ?? def.label;

          return (
            <div key={def.id} className="flex items-center gap-3">
              <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center">
                {status === "complete" && (
                  <svg className="w-5 h-5" style={{ color: "#2d00ff" }} fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                )}
                {status === "active" && (
                  <svg className="w-5 h-5 animate-spin" style={{ color: "#2d00ff" }} fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                )}
                {status === "pending" && (
                  <div className="w-5 h-5 rounded-full" style={{ border: "2px solid rgba(45,0,255,0.3)" }} />
                )}
                {status === "error" && (
                  <svg className="w-5 h-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                )}
              </div>
              <span
                className="text-sm"
                style={{
                  color: status === "active" ? "#111111" : status === "complete" ? "#9ca3af" : "#6b7280",
                  fontWeight: status === "active" ? 500 : 400,
                }}
              >
                {label}
              </span>
            </div>
          );
        })}
      </div>

      <div className="mt-6 pt-4 space-y-1 border-t border-gray-100">
        <p style={{ color: "#2d00ff" }} className="text-xs font-semibold">
          AI will populate up to 50 investors
        </p>
        <p className="text-xs text-gray-400">
          Results appear as they're found — usually 30–45 seconds total
        </p>
      </div>
    </div>
  );
}

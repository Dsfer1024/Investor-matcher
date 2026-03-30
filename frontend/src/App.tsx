import { useState } from "react";
import InputForm from "./components/InputForm/InputForm";
import LoadingProgress from "./components/LoadingProgress/LoadingProgress";
import ResultsTable from "./components/ResultsTable/ResultsTable";
import { findInvestors } from "./api/client";
import type { Investor, ProgressStep, SearchFormData } from "./types/investor";

const FRACTAL_LOGO_WHITE =
  "https://cdn.prod.website-files.com/6145e9ed201e02bd634fcdf9/614cbc69252818f93d3b2f58_FractalWhite.svg";

type AppState = "idle" | "loading" | "results" | "error";

export default function App() {
  const [state, setState] = useState<AppState>("idle");
  const [progressSteps, setProgressSteps] = useState<ProgressStep[]>([]);
  const [investors, setInvestors] = useState<Investor[]>([]);
  const [quickThesis, setQuickThesis] = useState("");
  const [companyUrl, setCompanyUrl] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  function updateProgress(step: ProgressStep) {
    setProgressSteps((prev) => {
      const existing = prev.find((s) => s.id === step.id);
      if (existing) return prev.map((s) => (s.id === step.id ? step : s));
      return [...prev, step];
    });
  }

  async function handleSubmit(formData: SearchFormData) {
    setState("loading");
    setProgressSteps([]);
    setInvestors([]);
    setQuickThesis("");
    setCompanyUrl(formData.companyUrl);
    setErrorMsg("");

    await findInvestors(
      formData,
      updateProgress,
      (results, thesis) => {
        setInvestors(results);
        setQuickThesis(thesis);
        setState("results");
      },
      (err) => {
        setErrorMsg(err);
        setState("error");
      }
    );
  }

  function reset() {
    setState("idle");
    setProgressSteps([]);
    setInvestors([]);
    setQuickThesis("");
    setCompanyUrl("");
    setErrorMsg("");
  }

  return (
    <div className="min-h-screen" style={{ backgroundColor: "#00001b" }}>

      {/* Header */}
      <header style={{ backgroundColor: "#00001b", borderBottom: "1px solid rgba(45,0,255,0.25)" }} className="px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <img
              src={FRACTAL_LOGO_WHITE}
              alt="Fractal"
              className="h-7 w-auto"
            />
            <div style={{ width: "1px", height: "28px", backgroundColor: "rgba(45,0,255,0.4)" }} />
            <div>
              <p className="text-white font-semibold text-sm leading-tight">Investor Finder</p>
              <p style={{ color: "#cacaca" }} className="text-xs">AI-powered fundraising target list</p>
            </div>
          </div>
          {state !== "idle" && (
            <button
              onClick={reset}
              style={{ color: "#2d00ff", borderColor: "rgba(45,0,255,0.4)" }}
              className="text-sm border rounded-lg px-4 py-2 hover:bg-[#2d00ff] hover:text-white transition-colors"
            >
              ← New Search
            </button>
          )}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-10">

        {/* Idle — form */}
        {state === "idle" && (
          <div className="max-w-2xl mx-auto">
            <div className="mb-8 text-center">
              <h2 className="text-3xl font-bold text-white mb-2">Find Your Investors</h2>
              <p style={{ color: "#cacaca" }} className="text-sm">
                Enter your company details and we'll surface the most relevant investors,
                scored by AI and ranked by fit.
              </p>
            </div>
            <div className="bg-white rounded-2xl p-8 shadow-2xl">
              <InputForm onSubmit={handleSubmit} loading={false} />
            </div>
          </div>
        )}

        {/* Loading */}
        {state === "loading" && (
          <div className="max-w-md mx-auto">
            <LoadingProgress steps={progressSteps} />
          </div>
        )}

        {/* Error */}
        {state === "error" && (
          <div className="max-w-md mx-auto">
            <div
              style={{ backgroundColor: "rgba(45,0,255,0.08)", borderColor: "rgba(45,0,255,0.3)" }}
              className="border rounded-2xl p-6 text-center"
            >
              <p className="text-white font-medium mb-2">Something went wrong</p>
              <p style={{ color: "#cacaca" }} className="text-sm mb-5">{errorMsg}</p>
              <button
                onClick={reset}
                style={{ backgroundColor: "#2d00ff" }}
                className="px-5 py-2 text-white text-sm rounded-lg hover:opacity-90 transition-opacity"
              >
                Try Again
              </button>
            </div>
          </div>
        )}

        {/* Results */}
        {state === "results" && investors.length > 0 && (
          <ResultsTable investors={investors} quickThesis={quickThesis} companyUrl={companyUrl} />
        )}

        {/* Empty results */}
        {state === "results" && investors.length === 0 && (
          <div className="max-w-md mx-auto">
            <div
              style={{ backgroundColor: "rgba(45,0,255,0.08)", borderColor: "rgba(45,0,255,0.3)" }}
              className="border rounded-2xl p-6 text-center"
            >
              <p className="text-white font-medium mb-2">No investors returned</p>
              <p style={{ color: "#cacaca" }} className="text-sm mb-5">
                The AI research call completed but returned no results. Try adding more detail to your inputs.
              </p>
              <button
                onClick={reset}
                style={{ backgroundColor: "#2d00ff" }}
                className="px-5 py-2 text-white text-sm rounded-lg hover:opacity-90 transition-opacity"
              >
                Try Again
              </button>
            </div>
          </div>
        )}

      </main>

      {/* Footer */}
      <footer style={{ borderTop: "1px solid rgba(45,0,255,0.15)" }} className="mt-16 px-6 py-5">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <img src={FRACTAL_LOGO_WHITE} alt="Fractal" className="h-5 w-auto opacity-60" />
          <p style={{ color: "#666666" }} className="text-xs">
            Powered by Fractal × Claude AI
          </p>
        </div>
      </footer>

    </div>
  );
}

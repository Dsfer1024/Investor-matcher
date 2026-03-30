import { useState } from "react";
import InputForm from "./components/InputForm/InputForm";
import LoadingProgress from "./components/LoadingProgress/LoadingProgress";
import ResultsTable from "./components/ResultsTable/ResultsTable";
import { findInvestors } from "./api/client";
import type { Investor, ProgressStep, SearchFormData } from "./types/investor";

type AppState = "idle" | "loading" | "results" | "error";

export default function App() {
  const [state, setState] = useState<AppState>("idle");
  const [progressSteps, setProgressSteps] = useState<ProgressStep[]>([]);
  const [investors, setInvestors] = useState<Investor[]>([]);
  const [errorMsg, setErrorMsg] = useState("");

  function updateProgress(step: ProgressStep) {
    setProgressSteps((prev) => {
      const existing = prev.find((s) => s.id === step.id);
      if (existing) {
        return prev.map((s) => (s.id === step.id ? step : s));
      }
      return [...prev, step];
    });
  }

  async function handleSubmit(formData: SearchFormData) {
    setState("loading");
    setProgressSteps([]);
    setInvestors([]);
    setErrorMsg("");

    await findInvestors(
      formData,
      updateProgress,
      (results) => {
        setInvestors(results);
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
    setErrorMsg("");
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Investor Matcher</h1>
            <p className="text-sm text-gray-500">AI-powered fundraising target list</p>
          </div>
          {state !== "idle" && (
            <button
              onClick={reset}
              className="text-sm text-blue-600 hover:underline"
            >
              ← New Search
            </button>
          )}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {state === "idle" && (
          <div className="max-w-2xl mx-auto">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-1">Find Your Investors</h2>
              <p className="text-gray-500 text-sm">
                Enter your company details and we'll surface the top 100 most relevant investors,
                scored by AI and sorted by expected fit.
              </p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
              <InputForm onSubmit={handleSubmit} loading={false} />
            </div>
          </div>
        )}

        {state === "loading" && (
          <div className="max-w-md mx-auto">
            <LoadingProgress steps={progressSteps} />
          </div>
        )}

        {state === "error" && (
          <div className="max-w-md mx-auto">
            <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
              <p className="text-red-700 font-medium mb-2">Something went wrong</p>
              <p className="text-red-600 text-sm mb-4">{errorMsg}</p>
              <button
                onClick={reset}
                className="px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700"
              >
                Try Again
              </button>
            </div>
          </div>
        )}

        {state === "results" && investors.length > 0 && (
          <ResultsTable investors={investors} />
        )}
      </main>
    </div>
  );
}

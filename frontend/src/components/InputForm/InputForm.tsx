import { useState, FormEvent } from "react";
import MultiTagInput from "./MultiTagInput";
import MultiSelectDropdown from "./MultiSelectDropdown";
import {
  INDUSTRIES,
  KEYWORDS,
  ICP_SEGMENTS,
  ROUND_STAGES,
  INVESTOR_TYPES,
  type SearchFormData,
  type Keyword,
  type IcpSegment,
  type RoundStage,
  type InvestorType,
} from "../../types/investor";

interface Props {
  onSubmit: (data: SearchFormData) => void;
  loading: boolean;
}

const INITIAL: SearchFormData = {
  companyUrl: "",
  industries: [],
  icpSegments: [],
  arr: "",
  arrGrowth: "",
  raiseAmount: "",
  keywords: [],
  roundStage: "",
  investorTypes: [],
  furtherContext: "",
  competitors: [],
};

function isValidUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:";
  } catch {
    return false;
  }
}

function validateUrl(value: string): string | null {
  if (!value.startsWith("http://") && !value.startsWith("https://")) {
    return `Must start with https:// — e.g. https://${value.replace(/^www\./, "")}`;
  }
  if (!isValidUrl(value)) {
    return "Invalid URL format — please enter a valid web address";
  }
  return null;
}

export default function InputForm({ onSubmit, loading }: Props) {
  const [form, setForm] = useState<SearchFormData>(INITIAL);
  const [errors, setErrors] = useState<Partial<Record<keyof SearchFormData, string>>>({});

  function set<K extends keyof SearchFormData>(key: K, value: SearchFormData[K]) {
    setForm((f) => ({ ...f, [key]: value }));
    setErrors((e) => ({ ...e, [key]: undefined }));
  }

  function validate(): boolean {
    const errs: typeof errors = {};

    if (!form.companyUrl.trim()) {
      errs.companyUrl = "Required";
    } else {
      const urlErr = validateUrl(form.companyUrl.trim());
      if (urlErr) errs.companyUrl = urlErr;
    }

    if (form.industries.length === 0) errs.industries = "Select at least one industry";
    if (form.keywords.length === 0) errs.keywords = "Select at least one keyword";
    if (form.icpSegments.length === 0) errs.icpSegments = "Select at least one segment";
    if (form.investorTypes.length === 0) errs.investorTypes = "Select at least one investor type";
    if (!form.arr.trim()) errs.arr = "Required";
    if (!form.arrGrowth.trim()) errs.arrGrowth = "Required";
    if (!form.raiseAmount.trim()) errs.raiseAmount = "Required";
    if (!form.roundStage) errs.roundStage = "Required";
    if (form.competitors.length === 0) errs.competitors = "Add at least one competitor URL";

    // Validate any competitor URLs already in the list
    for (const url of form.competitors) {
      const err = validateUrl(url);
      if (err) {
        errs.competitors = `Invalid competitor URL "${url}" — ${err}`;
        break;
      }
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (validate()) onSubmit(form);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">

      {/* Company URL */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Company URL <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={form.companyUrl}
          onChange={(e) => set("companyUrl", e.target.value)}
          onBlur={() => {
            if (form.companyUrl.trim()) {
              const err = validateUrl(form.companyUrl.trim());
              if (err) setErrors((e) => ({ ...e, companyUrl: err }));
            }
          }}
          placeholder="https://yourcompany.com (must include https://)"
          className={`w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2d00ff] ${
            errors.companyUrl ? "border-red-400 bg-red-50" : "border-gray-300"
          }`}
        />
        {errors.companyUrl && <p className="text-xs text-red-500 mt-1">{errors.companyUrl}</p>}
      </div>

      {/* Industry + Keywords */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <MultiSelectDropdown
          label="Industry"
          options={INDUSTRIES}
          selected={form.industries}
          onChange={(v) => set("industries", v)}
          placeholder="Select industry..."
          required
          error={errors.industries}
          allowCustom
          customPlaceholder="Type your own and press Enter..."
        />
        <MultiSelectDropdown
          label="Keywords"
          options={KEYWORDS}
          selected={form.keywords}
          onChange={(v) => set("keywords", v as Keyword[])}
          placeholder="Select business type keywords..."
          required
          error={errors.keywords}
        />
      </div>

      {/* ICP + Round Stage */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <MultiSelectDropdown
          label="ICP / Target Customer"
          options={ICP_SEGMENTS}
          selected={form.icpSegments}
          onChange={(v) => set("icpSegments", v as IcpSegment[])}
          placeholder="Select customer segment(s)..."
          required
          error={errors.icpSegments}
        />
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Round Stage <span className="text-red-500">*</span>
          </label>
          <select
            value={form.roundStage}
            onChange={(e) => {
              const stage = e.target.value as RoundStage;
              set("roundStage", stage);
              if (stage === "Majority Buyout") {
                set("investorTypes", form.investorTypes.filter((t) => t !== "VC") as InvestorType[]);
              }
            }}
            className={`w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2d00ff] bg-white ${
              errors.roundStage ? "border-red-400 bg-red-50" : "border-gray-300"
            }`}
          >
            <option value="">Select stage</option>
            {ROUND_STAGES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          {errors.roundStage && <p className="text-xs text-red-500 mt-1">{errors.roundStage}</p>}
        </div>
      </div>

      {/* Investor Type */}
      <MultiSelectDropdown
        label="Investor Type"
        options={form.roundStage === "Majority Buyout"
          ? INVESTOR_TYPES.filter((t) => t !== "VC")
          : INVESTOR_TYPES}
        selected={form.investorTypes}
        onChange={(v) => set("investorTypes", v as InvestorType[])}
        placeholder="Select investor type(s)..."
        required
        error={errors.investorTypes}
      />
      {form.roundStage === "Majority Buyout" && (
        <p className="text-xs text-amber-600 -mt-3">
          VC is not available for Majority Buyout — only Growth Equity and Private Equity apply.
        </p>
      )}

      {/* ARR + ARR Growth + Desired Raise */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            ARR ($M) <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            min="0"
            step="0.1"
            value={form.arr}
            onChange={(e) => set("arr", e.target.value)}
            placeholder="e.g. 2.5"
            className={`w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2d00ff] ${
              errors.arr ? "border-red-400 bg-red-50" : "border-gray-300"
            }`}
          />
          {errors.arr && <p className="text-xs text-red-500 mt-1">{errors.arr}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            ARR Growth YoY (%) <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            min="0"
            step="1"
            value={form.arrGrowth}
            onChange={(e) => set("arrGrowth", e.target.value)}
            placeholder="e.g. 150"
            className={`w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2d00ff] ${
              errors.arrGrowth ? "border-red-400 bg-red-50" : "border-gray-300"
            }`}
          />
          {errors.arrGrowth && <p className="text-xs text-red-500 mt-1">{errors.arrGrowth}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Desired Amount to Raise ($M) <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            min="0"
            step="0.5"
            value={form.raiseAmount}
            onChange={(e) => set("raiseAmount", e.target.value)}
            placeholder="e.g. 10"
            className={`w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2d00ff] ${
              errors.raiseAmount ? "border-red-400 bg-red-50" : "border-gray-300"
            }`}
          />
          {errors.raiseAmount && <p className="text-xs text-red-500 mt-1">{errors.raiseAmount}</p>}
        </div>
      </div>

      {/* Competitor URLs */}
      <div>
        <MultiTagInput
          label="Competitor URLs *"
          placeholder="Paste a competitor URL (must include https://) and press Enter. Add as many as relevant."
          values={form.competitors}
          onChange={(v) => set("competitors", v)}
          validate={validateUrl}
        />
        {errors.competitors && <p className="text-xs text-red-500 mt-1">{errors.competitors}</p>}
      </div>

      {/* Further Context */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Further Context <span className="text-gray-400 font-normal">(optional)</span>
        </label>
        <textarea
          value={form.furtherContext}
          onChange={(e) => set("furtherContext", e.target.value)}
          placeholder="Additional details about your business, traction, differentiation, or what you're looking for in an investor..."
          rows={3}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2d00ff] resize-none"
        />
      </div>

      <button
        type="submit"
        disabled={loading}
        style={{ backgroundColor: loading ? "#0f0087" : "#2d00ff" }}
        className="w-full py-3 px-6 text-white font-semibold rounded-lg transition-opacity text-sm hover:opacity-90 disabled:opacity-60"
      >
        {loading ? "Finding investors..." : "Find My Investors →"}
      </button>
    </form>
  );
}

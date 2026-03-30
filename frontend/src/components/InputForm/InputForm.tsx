import { useState, FormEvent } from "react";
import MultiTagInput from "./MultiTagInput";
import FileUpload from "./FileUpload";
import { BUSINESS_TYPES, ROUND_STAGES, type SearchFormData, type BusinessType, type RoundStage } from "../../types/investor";

interface Props {
  onSubmit: (data: SearchFormData) => void;
  loading: boolean;
}

const INITIAL: SearchFormData = {
  companyUrl: "",
  broadIndustry: "",
  targetCustomer: "",
  arr: "",
  arrGrowth: "",
  businessTypes: [],
  roundStage: "",
  furtherContext: "",
  competitors: [],
  spreadsheetFile: null,
};

export default function InputForm({ onSubmit, loading }: Props) {
  const [form, setForm] = useState<SearchFormData>(INITIAL);
  const [errors, setErrors] = useState<Partial<Record<keyof SearchFormData, string>>>({});

  function set<K extends keyof SearchFormData>(key: K, value: SearchFormData[K]) {
    setForm((f) => ({ ...f, [key]: value }));
    setErrors((e) => ({ ...e, [key]: undefined }));
  }

  function toggleBusinessType(type: BusinessType) {
    set(
      "businessTypes",
      form.businessTypes.includes(type)
        ? form.businessTypes.filter((t) => t !== type)
        : [...form.businessTypes, type]
    );
  }

  function validate(): boolean {
    const errs: typeof errors = {};
    if (!form.companyUrl.trim()) errs.companyUrl = "Company URL is required";
    if (!form.roundStage) errs.roundStage = "Round stage is required";
    if (form.businessTypes.length === 0) errs.businessTypes = "Select at least one business type";
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (validate()) onSubmit(form);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Row 1: URL + Industry */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Company URL <span className="text-red-500">*</span>
          </label>
          <input
            type="url"
            value={form.companyUrl}
            onChange={(e) => set("companyUrl", e.target.value)}
            placeholder="https://yourcompany.com"
            className={`w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.companyUrl ? "border-red-400" : "border-gray-300"
            }`}
          />
          {errors.companyUrl && <p className="text-xs text-red-500 mt-1">{errors.companyUrl}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Broad Industry</label>
          <input
            type="text"
            value={form.broadIndustry}
            onChange={(e) => set("broadIndustry", e.target.value)}
            placeholder="e.g. Construction Tech, Legal AI, Logistics"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Target Customer */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Target Customer / ICP
        </label>
        <textarea
          value={form.targetCustomer}
          onChange={(e) => set("targetCustomer", e.target.value)}
          placeholder="Describe your ideal customer in detail (e.g. mid-market law firms with 50-500 attorneys in North America, currently using legacy document management software)"
          rows={3}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
        />
      </div>

      {/* Row 2: ARR + Growth + Stage */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">ARR ($M)</label>
          <input
            type="number"
            min="0"
            step="0.1"
            value={form.arr}
            onChange={(e) => set("arr", e.target.value)}
            placeholder="e.g. 2.5"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">ARR Growth YoY (%)</label>
          <input
            type="number"
            min="0"
            step="1"
            value={form.arrGrowth}
            onChange={(e) => set("arrGrowth", e.target.value)}
            placeholder="e.g. 150"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Round Stage <span className="text-red-500">*</span>
          </label>
          <select
            value={form.roundStage}
            onChange={(e) => set("roundStage", e.target.value as RoundStage)}
            className={`w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white ${
              errors.roundStage ? "border-red-400" : "border-gray-300"
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

      {/* Business Types */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Business Type <span className="text-red-500">*</span>{" "}
          <span className="font-normal text-gray-400">(select all that apply)</span>
        </label>
        <div className="flex flex-wrap gap-2">
          {BUSINESS_TYPES.map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => toggleBusinessType(type)}
              className={`px-3 py-1.5 rounded-full text-sm border transition-colors ${
                form.businessTypes.includes(type)
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-gray-700 border-gray-300 hover:border-blue-400"
              }`}
            >
              {type}
            </button>
          ))}
        </div>
        {errors.businessTypes && (
          <p className="text-xs text-red-500 mt-1">{errors.businessTypes}</p>
        )}
      </div>

      {/* Further Context */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Further Context</label>
        <textarea
          value={form.furtherContext}
          onChange={(e) => set("furtherContext", e.target.value)}
          placeholder="Additional details about your business, traction, differentiation, or what you're looking for in an investor..."
          rows={4}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
        />
      </div>

      {/* Competitors */}
      <MultiTagInput
        label="Competitors"
        placeholder="Type a competitor name and press Enter..."
        values={form.competitors}
        onChange={(v) => set("competitors", v)}
      />

      {/* File Upload */}
      <div>
        <FileUpload
          file={form.spreadsheetFile}
          onChange={(f) => set("spreadsheetFile", f)}
        />
        <p className="text-xs text-gray-400 mt-1.5">
          AI generates investors automatically. Your spreadsheet adds extra candidates.
        </p>
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={loading}
        className="w-full py-3 px-6 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold rounded-lg transition-colors text-sm"
      >
        {loading ? "Finding investors..." : "Find My Investors"}
      </button>
    </form>
  );
}

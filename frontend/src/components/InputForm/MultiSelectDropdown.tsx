import { useState, useRef, useEffect, KeyboardEvent } from "react";

interface Props {
  label: string;
  options: readonly string[];
  selected: string[];
  onChange: (selected: string[]) => void;
  placeholder?: string;
  required?: boolean;
  error?: string;
  allowCustom?: boolean;
  customPlaceholder?: string;
}

export default function MultiSelectDropdown({
  label,
  options,
  selected,
  onChange,
  placeholder = "Select options...",
  required,
  error,
  allowCustom = false,
  customPlaceholder = "Type and press Enter to add...",
}: Props) {
  const [open, setOpen] = useState(false);
  const [customInput, setCustomInput] = useState("");
  const [extraOptions, setExtraOptions] = useState<string[]>([]);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function toggle(option: string) {
    if (selected.includes(option)) {
      onChange(selected.filter((s) => s !== option));
    } else {
      onChange([...selected, option]);
    }
  }

  function addCustom() {
    const val = customInput.trim();
    if (!val) return;
    if (!selected.includes(val)) {
      onChange([...selected, val]);
    }
    if (!options.includes(val) && !extraOptions.includes(val)) {
      setExtraOptions((e) => [...e, val]);
    }
    setCustomInput("");
  }

  function handleCustomKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      addCustom();
    }
  }

  const allOptions = [...options, ...extraOptions];

  const displayText =
    selected.length === 0
      ? placeholder
      : selected.length === 1
      ? selected[0]
      : `${selected[0]} +${selected.length - 1} more`;

  return (
    <div ref={ref} className="relative">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}
        {required && <span className="text-red-500 ml-0.5">*</span>}
      </label>

      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`w-full flex items-center justify-between border rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 ${
          error ? "border-red-400" : "border-gray-300"
        }`}
      >
        <span className={selected.length === 0 ? "text-gray-400" : "text-gray-800"}>
          {displayText}
        </span>
        <svg
          className={`w-4 h-4 text-gray-400 flex-shrink-0 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute z-20 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg">
          <div className="max-h-52 overflow-y-auto">
            {allOptions.map((option) => {
              const checked = selected.includes(option);
              return (
                <label
                  key={option}
                  className="flex items-center gap-3 px-3 py-2 hover:bg-gray-50 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggle(option)}
                    className="w-4 h-4 accent-blue-600 cursor-pointer"
                  />
                  <span className="text-sm text-gray-700">{option}</span>
                </label>
              );
            })}
          </div>

          {allowCustom && (
            <div className="border-t border-gray-100 px-3 py-2">
              <input
                type="text"
                value={customInput}
                onChange={(e) => setCustomInput(e.target.value)}
                onKeyDown={handleCustomKey}
                placeholder={customPlaceholder}
                className="w-full text-sm border border-gray-200 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500 placeholder-gray-400"
              />
            </div>
          )}

          {selected.length > 0 && (
            <div className="border-t border-gray-100">
              <button
                type="button"
                onClick={() => onChange([])}
                className="w-full text-xs text-red-500 hover:text-red-700 py-1.5 text-center"
              >
                Clear all
              </button>
            </div>
          )}
        </div>
      )}

      {selected.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1.5">
          {selected.map((s) => (
            <span
              key={s}
              className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded-md"
            >
              {s}
              <button
                type="button"
                onClick={() => toggle(s)}
                className="text-blue-500 hover:text-blue-700 leading-none"
              >
                &times;
              </button>
            </span>
          ))}
        </div>
      )}

      {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
    </div>
  );
}

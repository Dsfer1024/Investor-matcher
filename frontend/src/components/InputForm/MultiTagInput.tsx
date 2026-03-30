import { useState, KeyboardEvent } from "react";

interface Props {
  label: string;
  placeholder?: string;
  values: string[];
  onChange: (values: string[]) => void;
  validate?: (value: string) => string | null; // returns error message or null
}

export default function MultiTagInput({ label, placeholder, values, onChange, validate }: Props) {
  const [input, setInput] = useState("");
  const [tagError, setTagError] = useState<string | null>(null);

  function addTag() {
    const trimmed = input.trim();
    if (!trimmed) return;

    if (validate) {
      const err = validate(trimmed);
      if (err) {
        setTagError(err);
        return;
      }
    }

    if (!values.includes(trimmed)) {
      onChange([...values, trimmed]);
    }
    setInput("");
    setTagError(null);
  }

  function handleKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTag();
    } else if (e.key === "Backspace" && input === "" && values.length > 0) {
      onChange(values.slice(0, -1));
    } else {
      setTagError(null);
    }
  }

  function remove(tag: string) {
    onChange(values.filter((v) => v !== tag));
  }

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <div className={`flex flex-wrap gap-2 p-2 border rounded-lg bg-white min-h-[42px] focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 ${tagError ? "border-red-400" : "border-gray-300"}`}>
        {values.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 text-blue-800 text-sm rounded-md"
          >
            {tag}
            <button
              type="button"
              onClick={() => remove(tag)}
              className="text-blue-500 hover:text-blue-700 leading-none"
            >
              &times;
            </button>
          </span>
        ))}
        <input
          type="text"
          value={input}
          onChange={(e) => { setInput(e.target.value); setTagError(null); }}
          onKeyDown={handleKey}
          onBlur={addTag}
          placeholder={values.length === 0 ? placeholder : ""}
          className="flex-1 min-w-[120px] outline-none text-sm bg-transparent"
        />
      </div>
      {tagError
        ? <p className="text-xs text-red-500 mt-1">{tagError}</p>
        : <p className="text-xs text-gray-400 mt-1">Press Enter to add</p>
      }
    </div>
  );
}

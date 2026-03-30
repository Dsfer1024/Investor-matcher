import { useRef, DragEvent } from "react";

interface Props {
  file: File | null;
  onChange: (file: File | null) => void;
}

export default function FileUpload({ file, onChange }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    const dropped = e.dataTransfer.files[0];
    if (dropped) onChange(dropped);
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    onChange(e.target.files?.[0] ?? null);
  }

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        Supplemental Investor Spreadsheet{" "}
        <span className="font-normal text-gray-400">(optional — CSV or Excel)</span>
      </label>
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={() => inputRef.current?.click()}
        className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors"
      >
        {file ? (
          <div className="flex items-center justify-center gap-2">
            <span className="text-sm font-medium text-gray-700">{file.name}</span>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onChange(null);
                if (inputRef.current) inputRef.current.value = "";
              }}
              className="text-red-400 hover:text-red-600 text-xs"
            >
              Remove
            </button>
          </div>
        ) : (
          <div className="text-sm text-gray-500">
            <span className="font-medium text-blue-600">Click to upload</span> or drag & drop
            <br />
            <span className="text-xs">.csv or .xlsx</span>
          </div>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={handleChange}
          className="hidden"
        />
      </div>
      <p className="text-xs text-gray-400 mt-1">
        <a href="/investor_template.csv" download className="underline hover:text-blue-500">
          Download template
        </a>
      </p>
    </div>
  );
}

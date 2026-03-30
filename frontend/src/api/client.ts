import type { Investor, ProgressStep, SearchFormData } from "../types/investor";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function findInvestors(
  formData: SearchFormData,
  onProgress: (step: ProgressStep) => void,
  onResult: (investors: Investor[]) => void,
  onError: (error: string) => void
): Promise<void> {
  const { spreadsheetFile, ...rest } = formData;

  const body = new FormData();
  body.append("data", JSON.stringify(rest));
  if (spreadsheetFile) {
    body.append("file", spreadsheetFile);
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/find-investors`, {
      method: "POST",
      body,
    });
  } catch (err) {
    onError("Could not connect to the server. Is the backend running?");
    return;
  }

  if (!response.ok) {
    onError(`Server error: ${response.status} ${response.statusText}`);
    return;
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";

    for (const chunk of chunks) {
      const line = chunk.trim();
      if (!line.startsWith("data: ")) continue;
      try {
        const event = JSON.parse(line.slice(6));
        if (event.type === "progress") {
          onProgress(event.step as ProgressStep);
        } else if (event.type === "result") {
          onResult(event.investors as Investor[]);
        } else if (event.type === "error") {
          onError(event.message as string);
        }
      } catch {
        // Malformed SSE line — ignore
      }
    }
  }
}

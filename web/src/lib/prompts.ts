import type { DashboardContext } from "./types";
import { serviceUrl } from "./format";

export function buildSavePrompt(contexts: DashboardContext[]): string {
  const slotLines = contexts
    .map((item) => `Slot ${item.slot_number}: slot_name="${item.slot_name}"`)
    .join("\n");

  return [
    `A2CR service: ${serviceUrl()}`,
    "Use the A2CR MCP tool. Do not guess or call direct HTTP API endpoints.",
    "Save the current work with save_context.",
    "Use compact detail for Free. Use detailed only when the account allows it and the extra detail improves resume quality.",
    "If you can estimate the source context length, pass original_length so A2CR can show estimated tokens saved.",
    "Never save secrets, API keys, Authorization headers, private database URLs, full transcripts, or long logs.",
    slotLines ? `Known fixed slots:\n${slotLines}` : "No fixed slots are currently active.",
    "Return the resume_prompt after saving."
  ].join("\n");
}

export function buildGenericResumePrompt(): string {
  return [
    `A2CR service: ${serviceUrl()}`,
    "Use the A2CR MCP tool. Do not guess or call direct HTTP API endpoints.",
    "First run resume_context(). If multiple candidates are returned, show the candidates and ask me which slot to use.",
    "After loading, you may inspect the project files normally as needed.",
    "Respond in the language of this message."
  ].join("\n");
}

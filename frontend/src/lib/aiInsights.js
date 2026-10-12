import { apiClient } from "./apiClient";
import { downloadFile } from "./download";

// AI Statement Insights: pick a date range, get a financial summary,
// category breakdown, budget comparison, a comparison against the previous
// equivalent period, unusual-spending/recurring-charge detection, saving
// opportunities, and a set of individually-cited key insights - plus a
// short AI narrative on top (real when the backend has an OPENAI_API_KEY
// configured, otherwise an honest computed fallback - the response always
// says which one you got via `ai_generated`).
export async function analyzeStatement({ startDate, endDate }) {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
  return apiClient.get(`/insights/statement/analyze?${params.toString()}`, { auth: true });
}

// "Ask AI about this period" - restricted to the selected date range unless
// the question itself asks for a comparison (e.g. mentions "last month").
export async function askAboutStatement({ startDate, endDate, question }) {
  return apiClient.post(
    "/insights/statement/ask",
    { start_date: startDate, end_date: endDate, question },
    { auth: true }
  );
}

// Downloads the same analysis as a PDF or CSV - summary, category
// breakdown, AI key insights, and the full transaction list.
export async function downloadAIStatementReport({ startDate, endDate, format }) {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate, format });
  await downloadFile(
    `/insights/statement/report?${params.toString()}`,
    `ai_statement_${startDate}_to_${endDate}.${format}`
  );
}

import { apiClient } from "./apiClient";

export async function recommendBudgets({ windowMonths } = {}) {
  const params = new URLSearchParams();
  if (windowMonths) params.set("window_months", windowMonths);
  const qs = params.toString();
  return apiClient.post(`/budgets/recommend${qs ? `?${qs}` : ""}`, undefined, { auth: true });
}

export async function generateForecast({ daysAhead } = {}) {
  const params = new URLSearchParams();
  if (daysAhead) params.set("days_ahead", daysAhead);
  const qs = params.toString();
  return apiClient.post(`/forecasts${qs ? `?${qs}` : ""}`, undefined, { auth: true });
}

export async function detectAnomalies() {
  return apiClient.post("/anomalies", undefined, { auth: true });
}

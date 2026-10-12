import { apiClient } from "./apiClient";

// The current month's budgets exactly as stored - both AI-recommended and
// user-created/edited. Unlike recommendBudgets(), this never changes
// anything server-side, so it's safe to call every time the Dashboard
// mounts without undoing an edit or resurrecting a delete.
export async function fetchBudgets() {
  return apiClient.get("/budgets", { auth: true });
}

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

export async function createBudget({ categoryName, amount }) {
  return apiClient.post("/budgets", { category_name: categoryName, amount }, { auth: true });
}

export async function updateBudget(budgetId, amount) {
  return apiClient.patch(`/budgets/${budgetId}`, { amount }, { auth: true });
}

export async function deleteBudget(budgetId) {
  return apiClient.delete(`/budgets/${budgetId}`, { auth: true });
}

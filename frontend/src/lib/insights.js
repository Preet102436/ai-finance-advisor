import { apiClient } from "./apiClient";

export async function fetchFinancialSummary() {
  return apiClient.get("/insights/summary", { auth: true });
}

export async function fetchMoneyRadar() {
  return apiClient.get("/insights/money-radar", { auth: true });
}

import { apiClient } from "./apiClient";

export async function fetchInsights() {
  return apiClient.get("/insights", { auth: true });
}

export async function fetchRecentAnomalies() {
  return apiClient.get("/anomalies", { auth: true });
}

import { apiClient } from "./apiClient";

export async function fetchConsent() {
  return apiClient.get("/settings", { auth: true });
}

export async function updateConsent(consent) {
  return apiClient.put("/settings", { data_processing_consent: consent }, { auth: true });
}

export async function deleteMyAccount() {
  return apiClient.delete("/users/me", { auth: true });
}

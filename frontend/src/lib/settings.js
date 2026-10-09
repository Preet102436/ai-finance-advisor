import { apiClient } from "./apiClient";

export async function fetchSettings() {
  return apiClient.get("/settings", { auth: true });
}

export async function updateConsent(consent) {
  return apiClient.put("/settings", { data_processing_consent: consent }, { auth: true });
}

export async function updateAiEnabled(enabled) {
  return apiClient.put("/settings", { ai_enabled: enabled }, { auth: true });
}

export async function deleteMyAccount() {
  return apiClient.delete("/users/me", { auth: true });
}

export async function fetchProfile() {
  return apiClient.get("/users/me/profile", { auth: true });
}

export async function updateProfile(payload) {
  return apiClient.put("/users/me/profile", payload, { auth: true });
}

export async function fetchBankAccounts() {
  return apiClient.get("/bank/accounts", { auth: true });
}

export async function disconnectBankAccount(accountId) {
  return apiClient.delete(`/bank/accounts/${accountId}`, { auth: true });
}

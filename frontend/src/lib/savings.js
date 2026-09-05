import { apiClient } from "./apiClient";

export async function fetchSavingsSuggestions() {
  return apiClient.get("/savings/suggestions", { auth: true });
}

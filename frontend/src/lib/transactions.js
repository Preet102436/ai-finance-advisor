import { apiClient } from "./apiClient";

export async function fetchTransactions({ categoryId, startDate, endDate } = {}) {
  const params = new URLSearchParams();
  if (categoryId) params.set("category_id", categoryId);
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const qs = params.toString();
  return apiClient.get(`/transactions${qs ? `?${qs}` : ""}`, { auth: true });
}

export async function fetchTransactionCategories() {
  return apiClient.get("/transactions/categories", { auth: true });
}

export async function syncBankAccount() {
  return apiClient.post("/bank/sync", undefined, { auth: true });
}

export async function uploadReceipt(file) {
  const formData = new FormData();
  formData.append("file", file);
  return apiClient.postForm("/receipts/upload", formData, { auth: true });
}

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

export async function linkBankAccount() {
  // Two-step OAuth-style flow (see backend/expense-ocr/link_account_api.py):
  // /bank/link-account issues an authorisation code, which /callback then
  // exchanges for a token and persists as a bank_accounts row.
  const { auth_code, state } = await apiClient.post("/bank/link-account", undefined, { auth: true });
  return apiClient.post(
    "/bank/link-account/callback",
    { auth_code, state },
    { auth: true }
  );
}

export async function syncBankAccount() {
  return apiClient.post("/bank/sync", undefined, { auth: true });
}

export async function uploadReceipt(file) {
  const formData = new FormData();
  formData.append("file", file);
  return apiClient.postForm("/receipts/upload", formData, { auth: true });
}

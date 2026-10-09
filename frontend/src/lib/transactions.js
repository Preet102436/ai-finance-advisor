import { apiClient } from "./apiClient";

export async function fetchTransactions({ categoryId, startDate, endDate, search, source } = {}) {
  const params = new URLSearchParams();
  if (categoryId) params.set("category_id", categoryId);
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  if (search) params.set("search", search);
  if (source) params.set("source", source);
  const qs = params.toString();
  return apiClient.get(`/transactions${qs ? `?${qs}` : ""}`, { auth: true });
}

export async function fetchTransaction(transactionId) {
  return apiClient.get(`/transactions/${transactionId}`, { auth: true });
}

export async function fetchTransactionCategories() {
  return apiClient.get("/transactions/categories", { auth: true });
}

export async function createTransaction(payload) {
  return apiClient.post("/transactions", payload, { auth: true });
}

export async function importTransactionsCsv(file) {
  const formData = new FormData();
  formData.append("file", file);
  return apiClient.postForm("/transactions/import-csv", formData, { auth: true });
}

export async function updateTransactionCategory(transactionId, categoryName) {
  return apiClient.put(
    `/transactions/${transactionId}/category`,
    { category_name: categoryName },
    { auth: true }
  );
}

// Two-step OAuth-style bank link flow (see backend/expense-ocr/link_account_api.py):
// step 1 issues an authorisation code (the "consent" step in the UI), step 2
// exchanges it for a token and persists the bank_accounts row (the "select
// account / connect" step). Split into two functions so the wizard UI can
// show each step as it actually happens, instead of one instant jump.
export async function startBankLink() {
  return apiClient.post("/bank/link-account", undefined, { auth: true });
}

export async function completeBankLink(authCode, state, { accountType, accountNumberDisplay } = {}) {
  return apiClient.post(
    "/bank/link-account/callback",
    {
      auth_code: authCode,
      state,
      account_type: accountType,
      account_number_display: accountNumberDisplay,
    },
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

export async function confirmReceipt(receiptId, payload) {
  return apiClient.post(`/receipts/${receiptId}/confirm`, payload, { auth: true });
}

export async function fetchReceiptForTransaction(transactionId) {
  return apiClient.get(`/receipts/by-transaction/${transactionId}`, { auth: true });
}

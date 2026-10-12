import { apiClient } from "./apiClient";

// Omit limit/offset to get every matching transaction back as a plain
// array (what the Dashboard's month-to-date spending breakdown wants).
// Pass limit to get a paginated page back instead - the Transactions
// page does this; the response shape then becomes
// { items, total, limit, offset } rather than a plain array.
export async function fetchTransactions({ categoryId, startDate, endDate, search, limit, offset } = {}) {
  const params = new URLSearchParams();
  if (categoryId) params.set("category_id", categoryId);
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  if (search) params.set("search", search);
  if (limit !== undefined) params.set("limit", limit);
  if (offset !== undefined) params.set("offset", offset);
  const qs = params.toString();
  return apiClient.get(`/transactions${qs ? `?${qs}` : ""}`, { auth: true });
}

export async function fetchTransactionCategories() {
  return apiClient.get("/transactions/categories", { auth: true });
}

export async function fetchBankAccounts() {
  return apiClient.get("/bank/accounts", { auth: true });
}

// Unlinks a bank account - its transactions go with it (the backend
// cascades that), freeing the user up to link a different one.
export async function deleteBankAccount(accountId) {
  return apiClient.delete(`/bank/accounts/${accountId}`, { auth: true });
}

// accountId is only needed when the user has more than one linked account -
// /bank/sync 400s with "Multiple accounts found" otherwise.
export async function syncBankAccount(accountId) {
  const qs = accountId ? `?account_id=${accountId}` : "";
  return apiClient.post(`/bank/sync${qs}`, undefined, { auth: true });
}

export async function uploadReceipt(file, accountId) {
  const formData = new FormData();
  formData.append("file", file);
  const qs = accountId ? `?account_id=${accountId}` : "";
  return apiClient.postForm(`/receipts/upload${qs}`, formData, { auth: true });
}

// Finalises a scanned receipt with the user's reviewed (possibly corrected)
// total/category/merchant/date - uploadReceipt() above already created the
// linked transaction with the OCR-predicted values; this applies whatever
// the user confirmed over the top of it. Used by ReceiptPreviewModal.jsx.
export async function confirmReceipt(receiptId, { total, category_name, merchant, txn_date }) {
  return apiClient.post(
    `/receipts/${receiptId}/confirm`,
    { total, category_name, merchant, txn_date },
    { auth: true }
  );
}

export async function importTransactions(file) {
  const formData = new FormData();
  formData.append("file", file);
  return apiClient.postForm("/transactions/import", formData, { auth: true });
}

export async function addTransaction({ txnDate, amount, merchant, description, categoryName }) {
  return apiClient.post(
    "/transactions",
    {
      txn_date: txnDate,
      amount,
      merchant: merchant || undefined,
      description: description || undefined,
      category_name: categoryName || undefined,
    },
    { auth: true }
  );
}

// Edits any transaction in place, however it got there (bank sync, manual
// entry, import, or a scanned receipt) - only the fields passed get changed.
export async function updateTransaction(transactionId, { txnDate, amount, merchant, description, categoryName } = {}) {
  return apiClient.put(
    `/transactions/${transactionId}`,
    {
      txn_date: txnDate,
      amount,
      merchant,
      description,
      category_name: categoryName,
    },
    { auth: true }
  );
}

export async function deleteTransaction(transactionId) {
  return apiClient.delete(`/transactions/${transactionId}`, { auth: true });
}

// Two-step, consent-only bank-link flow - no bank login screen, nothing to
// type (backend/expense-ocr/link_account_api.py). Step 1 posts consent and
// gets back an auth code; step 2 exchanges that code, completing the link.
// Used by components/BankLinkModal.jsx's wizard.
export async function startBankLink() {
  return apiClient.post("/bank/link-account", { consent: true }, { auth: true });
}

export async function completeBankLink(authCode, state) {
  return apiClient.post(
    "/bank/link-account/callback",
    { auth_code: authCode, state },
    { auth: true }
  );
}

// Older single-call wrapper around the same two endpoints, still used by
// TransactionsPage.jsx's inline link form. username/password are accepted
// for backwards compatibility but no longer required or checked by the
// backend - see startBankLink() above for the current no-login flow.
export async function linkBankAccount({ consent, username, password }) {
  const step1 = await apiClient.post(
    "/bank/link-account",
    { consent, username, password },
    { auth: true }
  );
  return apiClient.post(
    "/bank/link-account/callback",
    { auth_code: step1.auth_code, state: step1.state },
    { auth: true }
  );
}

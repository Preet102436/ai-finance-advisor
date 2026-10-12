import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  addTransaction,
  deleteBankAccount,
  deleteTransaction,
  fetchBankAccounts,
  fetchTransactionCategories,
  fetchTransactions,
  importTransactions,
  linkBankAccount,
  syncBankAccount,
  updateTransaction,
  uploadReceipt,
} from "../lib/transactions";
import { formatCurrency, formatDate } from "../lib/format";

const EMPTY_FILTERS = { categoryId: "", startDate: "", endDate: "" };
const PAGE_SIZE = 25;

// Mocked Open Banking sandbox login (see backend/expense-ocr/sandbox_auth_test.py).
const DEMO_BANK_USERNAME = "demo_user";
const DEMO_BANK_PASSWORD = "demo1234";

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

const EMPTY_NEW_TRANSACTION = {
  txnDate: "",
  direction: "expense",
  amount: "",
  merchant: "",
  description: "",
  categoryName: "",
};

export default function TransactionsPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [transactions, setTransactions] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [categories, setCategories] = useState([]);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState(null);

  // Only shown once there's actually more than one linked account - most
  // users have exactly one and never see this. /bank/sync and
  // /receipts/upload both need to know which account when there's a choice.
  // Only one bank account is ever linked at a time (link / unlink, not
  // multiple) - no picker needed, and /bank/sync and /receipts/upload both
  // resolve to "the" account on their own when there's exactly one.
  const [bankAccounts, setBankAccounts] = useState([]);
  const [unlinking, setUnlinking] = useState(false);

  // Per-row inline edit for a single transaction (edit/delete, any source).
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState(null);
  const [savingEdit, setSavingEdit] = useState(false);
  const [editError, setEditError] = useState("");

  const [showUploadForm, setShowUploadForm] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [uploadError, setUploadError] = useState("");

  // Manual transaction entry
  const [showAddForm, setShowAddForm] = useState(false);
  const [newTransaction, setNewTransaction] = useState(EMPTY_NEW_TRANSACTION);
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState("");

  // CSV/Excel import
  const [showImportForm, setShowImportForm] = useState(false);
  const [importFile, setImportFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [importError, setImportError] = useState("");

  // Bank-link consent + mock-credentials flow: 0 = hidden, 1 = consent, 2 = credentials
  const [linkStep, setLinkStep] = useState(0);
  const [consentChecked, setConsentChecked] = useState(false);
  const [credentials, setCredentials] = useState({ username: "", password: "" });
  const [linking, setLinking] = useState(false);
  const [linkError, setLinkError] = useState("");
  const [linkMessage, setLinkMessage] = useState(null);

  // "income" is the one category name the sandbox/manual data uses for money
  // coming in - filtering it out of expense suggestions (and only offering it
  // for income entries) avoids nonsensical combinations like an "income" expense.
  const categoryOptions =
    newTransaction.direction === "income"
      ? categories.filter((c) => c.name.toLowerCase() === "income")
      : categories.filter((c) => c.name.toLowerCase() !== "income");

  useEffect(() => {
    setLoading(true);
    setLoadError("");
    fetchTransactions({
      categoryId: appliedFilters.categoryId || undefined,
      startDate: appliedFilters.startDate || undefined,
      endDate: appliedFilters.endDate || undefined,
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
    })
      .then((result) => {
        setTransactions(result.items);
        setTotalCount(result.total);
      })
      .catch((err) => setLoadError(err.message || "Failed to load transactions"))
      .finally(() => setLoading(false));
  }, [appliedFilters, page]);

  function refreshCategories() {
    fetchTransactionCategories()
      .then(setCategories)
      .catch(() => {
        // Filter dropdown just stays as-is; the transaction list load above
        // surfaces the real error to the user.
      });
  }

  function loadBankAccounts() {
    fetchBankAccounts()
      .then(setBankAccounts)
      .catch(() => {
        // Request failed - leave whatever was already shown alone rather
        // than guessing; a real unlink/link action updates this directly
        // (see handleUnlink/handleLinkSubmit) so the button never depends
        // on this call succeeding to reflect what just happened.
      });
  }

  // Load once on mount - NOT on every filter change. It used to refetch
  // alongside every transaction load so newly synced categories would show
  // up in the dropdown, but that meant a fresh `categories` array landed
  // after every Clear/Apply too, which re-triggered the ?category= sync
  // effect below and silently re-applied a filter the URL still carried -
  // "Clear" would show everything for a moment and then snap back to the
  // filtered view. refreshCategories() is now called explicitly after
  // sync/upload/import/add instead, where a new category can actually show up.
  useEffect(() => {
    refreshCategories();
    loadBankAccounts();
  }, []);

  // "View expenses" links from the AI Insights / Money Radar panels land
  // here with ?category=NAME - resolve that to the matching category_id
  // and apply it as a filter once the category list has loaded, then clear
  // the URL param so it can't get silently re-applied later (same
  // self-clearing pattern the AI Advisor page uses for its own ?q= param).
  useEffect(() => {
    const categoryName = searchParams.get("category");
    if (!categoryName) return;
    if (categories.length === 0) return;
    const match = categories.find((c) => c.name.toLowerCase() === categoryName.toLowerCase());
    if (match) {
      const categoryId = String(match.category_id);
      setFilters((f) => (f.categoryId === categoryId ? f : { ...f, categoryId }));
      setAppliedFilters((f) => (f.categoryId === categoryId ? f : { ...f, categoryId }));
      setPage(1);
    }
    setSearchParams(
      (params) => {
        params.delete("category");
        return params;
      },
      { replace: true }
    );
  }, [categories, searchParams, setSearchParams]);

  function askAiQuestion(t) {
    const amount = `$${Math.abs(t.amount).toFixed(2)}`;
    const category = t.category_name || "this";
    const merchant = t.merchant ? ` at ${t.merchant}` : "";
    return `Tell me about my ${category} transaction of ${amount}${merchant} on ${t.txn_date}.`;
  }

  function askAiAboutTransaction(t) {
    navigate(`/chat?q=${encodeURIComponent(askAiQuestion(t))}`);
  }

  function startEdit(t) {
    setEditingId(t.transaction_id);
    setEditForm({
      txnDate: t.txn_date,
      amount: String(t.amount),
      merchant: t.merchant || "",
      description: t.description || "",
      categoryName: t.category_name || "",
    });
    setEditError("");
  }

  function cancelEdit() {
    setEditingId(null);
    setEditError("");
  }

  async function submitEdit(e) {
    e.preventDefault();
    const amount = parseFloat(editForm.amount);
    if (Number.isNaN(amount)) {
      setEditError("Enter a valid amount.");
      return;
    }
    setSavingEdit(true);
    setEditError("");
    try {
      await updateTransaction(editingId, {
        txnDate: editForm.txnDate,
        amount,
        merchant: editForm.merchant || "",
        description: editForm.description || "",
        categoryName: editForm.categoryName || "",
      });
      setEditingId(null);
      reloadTransactions();
      refreshCategories();
    } catch (err) {
      setEditError(err.message || "Failed to save changes");
    } finally {
      setSavingEdit(false);
    }
  }

  async function handleDeleteTransaction(t) {
    const label = t.merchant || t.category_name || "this transaction";
    const ok = window.confirm(`Delete ${label} (${formatDate(t.txn_date)})? This can't be undone.`);
    if (!ok) return;
    try {
      await deleteTransaction(t.transaction_id);
      reloadTransactions();
    } catch (err) {
      setLoadError(err.message || "Failed to delete transaction");
    }
  }

  function applyFilters(e) {
    e.preventDefault();
    setAppliedFilters(filters);
    setPage(1);
  }

  function clearFilters() {
    setFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
    setPage(1);
    setSearchParams({}, { replace: true });
  }

  function reloadTransactions() {
    setPage(1);
    setAppliedFilters((prev) => ({ ...prev }));
  }

  async function handleSync() {
    setSyncing(true);
    setSyncMessage(null);
    try {
      const result = await syncBankAccount();
      setSyncMessage({ type: "success", text: `Synced ${result.synced} new transaction(s).` });
      if (result.synced > 0) {
        reloadTransactions();
        refreshCategories();
      }
    } catch (err) {
      setSyncMessage({ type: "error", text: err.message || "Sync failed" });
    } finally {
      setSyncing(false);
    }
  }

  async function handleUpload(e) {
    e.preventDefault();
    if (!selectedFile) return;
    setUploading(true);
    setUploadError("");
    setUploadResult(null);
    try {
      const result = await uploadReceipt(selectedFile);
      setUploadResult(result);
      setSelectedFile(null);
      setShowUploadForm(false);
      e.target.reset();
      reloadTransactions();
      refreshCategories();
    } catch (err) {
      setUploadError(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function handleImport(e) {
    e.preventDefault();
    if (!importFile) return;
    setImporting(true);
    setImportError("");
    setImportResult(null);
    try {
      const result = await importTransactions(importFile);
      setImportResult(result);
      setImportFile(null);
      e.target.reset();
      if (result.imported > 0) {
        reloadTransactions();
        refreshCategories();
      }
    } catch (err) {
      setImportError(err.message || "Import failed");
    } finally {
      setImporting(false);
    }
  }

  function openAddForm() {
    setAddError("");
    setNewTransaction({ ...EMPTY_NEW_TRANSACTION, txnDate: todayIso() });
    setShowAddForm(true);
  }

  async function handleAddTransaction(e) {
    e.preventDefault();
    const amountValue = parseFloat(newTransaction.amount);
    if (Number.isNaN(amountValue) || amountValue <= 0) {
      setAddError("Enter an amount greater than 0.");
      return;
    }
    setAdding(true);
    setAddError("");
    try {
      await addTransaction({
        txnDate: newTransaction.txnDate,
        amount: newTransaction.direction === "expense" ? -Math.abs(amountValue) : Math.abs(amountValue),
        merchant: newTransaction.merchant.trim() || undefined,
        description: newTransaction.description.trim() || undefined,
        categoryName: newTransaction.categoryName.trim() || undefined,
      });
      setNewTransaction(EMPTY_NEW_TRANSACTION);
      setShowAddForm(false);
      reloadTransactions();
      refreshCategories();
    } catch (err) {
      setAddError(err.message || "Failed to add transaction");
    } finally {
      setAdding(false);
    }
  }

  function startLinkFlow() {
    setLinkMessage(null);
    setLinkError("");
    setConsentChecked(false);
    setCredentials({ username: "", password: "" });
    setLinkStep(1);
  }

  function cancelLinkFlow() {
    setLinkStep(0);
    setLinkError("");
    setCredentials({ username: "", password: "" });
  }

  function fillDemoCredentials() {
    setLinkError("");
    setCredentials({ username: DEMO_BANK_USERNAME, password: DEMO_BANK_PASSWORD });
  }

  function continueToCredentials() {
    if (!consentChecked) return;
    setLinkError("");
    setLinkStep(2);
  }

  async function handleLinkSubmit(e) {
    e.preventDefault();
    setLinking(true);
    setLinkError("");
    try {
      const result = await linkBankAccount({
        consent: consentChecked,
        username: credentials.username.trim(),
        password: credentials.password.trim(),
      });
      setLinkMessage({ type: "success", text: "Bank account linked. You can now sync transactions." });
      setLinkStep(0);
      // Switch the button to "Unlink account" immediately with a minimal
      // placeholder - loadBankAccounts() below fills in the real details
      // (provider name etc.) moments later without the button flickering back.
      if (result?.account_id) {
        setBankAccounts([{ account_id: result.account_id, provider_name: "your bank account" }]);
      }
      loadBankAccounts();
    } catch (err) {
      setLinkError(err.message || "Linking failed");
      // Clear the password so a retry is always typed fresh rather than
      // resubmitting a stale or browser-autofilled value.
      setCredentials((prev) => ({ ...prev, password: "" }));
    } finally {
      setLinking(false);
    }
  }

  async function handleUnlink(account) {
    const label = account.provider_name || "this bank account";
    const ok = window.confirm(`Do you want to unlink ${label}? This also removes its synced transactions. You can link a different account afterwards.`);
    if (!ok) return;
    setUnlinking(true);
    setLinkError("");
    try {
      await deleteBankAccount(account.account_id);
      // Switch the button back to "Link bank account" immediately - don't
      // wait on a re-fetch, which is what made this feel like it needed a
      // page refresh before.
      setBankAccounts([]);
      setLinkMessage({ type: "success", text: "Bank account unlinked. You can link a new one now." });
      loadBankAccounts();
      reloadTransactions();
    } catch (err) {
      setLinkMessage({ type: "error", text: err.message || "Failed to unlink account" });
    } finally {
      setUnlinking(false);
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Transactions</h1>
        <div className="page-header-actions">
          <button type="button" className="btn btn-secondary" onClick={showAddForm ? () => setShowAddForm(false) : openAddForm}>
            {showAddForm ? "Cancel" : "+ Add transaction"}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => {
              setUploadError("");
              setShowUploadForm((v) => !v);
            }}
          >
            {showUploadForm ? "Cancel" : "Upload receipt"}
          </button>
          {bankAccounts.length > 0 ? (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => handleUnlink(bankAccounts[0])}
              disabled={unlinking}
              title="Unlink this bank account so you can link a different one"
            >
              {unlinking ? "Unlinking..." : "Unlink account"}
            </button>
          ) : (
            <button type="button" className="btn btn-secondary" onClick={startLinkFlow}>
              Link bank account
            </button>
          )}
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => {
              setImportError("");
              setShowImportForm((v) => !v);
            }}
          >
            {showImportForm ? "Cancel" : "Import CSV/Excel"}
          </button>
          <button className="btn" onClick={handleSync} disabled={syncing}>
            {syncing ? "Syncing..." : "Sync bank account"}
          </button>
        </div>
      </div>

      {syncMessage && (
        <p className={syncMessage.type === "error" ? "status-banner status-error" : "status-banner status-success"}>
          {syncMessage.text}
        </p>
      )}
      {linkMessage && (
        <p className={linkMessage.type === "error" ? "status-banner status-error" : "status-banner status-success"}>
          {linkMessage.text}
        </p>
      )}

      {showAddForm && (
        <form className="add-transaction-card" onSubmit={handleAddTransaction}>
          <h2>Add a transaction</h2>
          <p>Record a one-off expense or income entry by hand - e.g. cash spending that never shows up via bank sync.</p>

          <div className="form-row">
            <label>
              Date
              <input
                type="date"
                value={newTransaction.txnDate}
                onChange={(e) => setNewTransaction({ ...newTransaction, txnDate: e.target.value })}
                required
              />
            </label>
            <label>
              Type
              <select
                value={newTransaction.direction}
                onChange={(e) => setNewTransaction({ ...newTransaction, direction: e.target.value })}
              >
                <option value="expense">Expense</option>
                <option value="income">Income</option>
              </select>
            </label>
            <label>
              Amount
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={newTransaction.amount}
                onChange={(e) => setNewTransaction({ ...newTransaction, amount: e.target.value })}
                placeholder="0.00"
                required
              />
            </label>
          </div>

          <div className="form-row">
            <label>
              Merchant
              <input
                type="text"
                value={newTransaction.merchant}
                onChange={(e) => setNewTransaction({ ...newTransaction, merchant: e.target.value })}
                placeholder="e.g. Woolworths"
              />
            </label>
            <label>
              Category
              <input
                type="text"
                list="category-options"
                value={newTransaction.categoryName}
                onChange={(e) => setNewTransaction({ ...newTransaction, categoryName: e.target.value })}
                placeholder={newTransaction.direction === "income" ? "e.g. income" : "e.g. groceries"}
              />
              <datalist id="category-options">
                {categoryOptions.map((c) => (
                  <option key={c.category_id} value={c.name} />
                ))}
              </datalist>
              <span className="field-hint">
                Pick an existing category, or type a new name to create one.
              </span>
            </label>
          </div>

          <label>
            Description
            <input
              type="text"
              value={newTransaction.description}
              onChange={(e) => setNewTransaction({ ...newTransaction, description: e.target.value })}
              placeholder="Optional note"
            />
          </label>

          {addError && <p className="status-banner status-error">{addError}</p>}

          <button type="submit" className="btn" disabled={adding}>
            {adding ? "Adding..." : "Add transaction"}
          </button>
        </form>
      )}

      {showImportForm && (
        <form className="add-transaction-card" onSubmit={handleImport}>
          <h2>Import transactions from a file</h2>
          <p>
            Upload a .csv or .xlsx export of your transaction history. Looks for date,
            amount, description and merchant columns (common header names are recognised
            automatically) and auto-categorizes rows where possible by merchant/description.
          </p>
          <input
            type="file"
            accept=".csv,.xlsx"
            onChange={(e) => setImportFile(e.target.files[0] || null)}
          />

          {importError && <p className="status-banner status-error">{importError}</p>}
          {importResult && (
            <p className="status-banner status-success">
              Imported {importResult.imported} transaction(s)
              {importResult.auto_categorized > 0 && `, auto-categorized ${importResult.auto_categorized}`}
              {importResult.skipped.length > 0 && `, skipped ${importResult.skipped.length} row(s) that could not be read`}
              .
            </p>
          )}

          <button type="submit" className="btn" disabled={!importFile || importing}>
            {importing ? "Importing..." : "Import"}
          </button>
        </form>
      )}

      {showUploadForm && (
        <form className="add-transaction-card" onSubmit={handleUpload}>
          <h2>Upload a receipt</h2>
          <p>We'll run OCR on it, guess the category and total, and add it as a transaction.</p>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => setSelectedFile(e.target.files[0] || null)}
          />

          {uploadError && <p className="status-banner status-error">{uploadError}</p>}
          {uploadResult && (
            <p className="status-banner status-success">
              Predicted category: <strong>{uploadResult.predicted_category}</strong> - predicted total:{" "}
              <strong>{formatCurrency(uploadResult.predicted_total)}</strong>
            </p>
          )}

          <button type="submit" className="btn" disabled={!selectedFile || uploading}>
            {uploading ? "Uploading..." : "Upload receipt"}
          </button>
        </form>
      )}

      {linkStep === 1 && (
        <div className="link-account-card">
          <h2>Link your bank account</h2>
          <p>
            This connects a sandbox/demo bank account so the app can read transaction data to
            build budgets, forecasts and chat answers. This is a mocked sandbox for development
            and demonstration only - no real bank credentials are ever used or stored.
          </p>
          <label className="consent-toggle">
            <input
              type="checkbox"
              checked={consentChecked}
              onChange={(e) => setConsentChecked(e.target.checked)}
            />
            I consent to this app accessing my (sandbox) transaction data to provide budgeting,
            forecasting and chat features.
          </label>

          {linkError && <p className="status-banner status-error">{linkError}</p>}

          <div className="form-row">
            <button type="button" className="btn" onClick={continueToCredentials} disabled={!consentChecked}>
              Continue
            </button>
            <button type="button" className="btn btn-secondary" onClick={cancelLinkFlow}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {linkStep === 2 && (
        <form className="link-account-card" onSubmit={handleLinkSubmit} autoComplete="off">
          <h2>Sign in to your bank (sandbox)</h2>
          <p>
            Demo sandbox login - use <strong>{DEMO_BANK_USERNAME}</strong> /{" "}
            <strong>{DEMO_BANK_PASSWORD}</strong>. No real bank login is involved; this stands in
            for the provider's own login screen.
          </p>
          <button type="button" className="btn btn-secondary btn-small" onClick={fillDemoCredentials}>
            Use demo credentials
          </button>
          {/* autoComplete is off/new-password on purpose: with "username" /
              "current-password" the browser autofilled this app's own saved
              login (email + app password) here, so the demo login kept
              failing with "Invalid bank sandbox username or password". */}
          <label>
            Username
            <input
              type="text"
              name="sandbox-bank-username"
              value={credentials.username}
              onChange={(e) => setCredentials({ ...credentials, username: e.target.value })}
              autoComplete="off"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              name="sandbox-bank-password"
              value={credentials.password}
              onChange={(e) => setCredentials({ ...credentials, password: e.target.value })}
              autoComplete="new-password"
              required
            />
          </label>

          {linkError && <p className="status-banner status-error">{linkError}</p>}

          <div className="form-row">
            <button type="submit" className="btn" disabled={linking}>
              {linking ? "Linking..." : "Link account"}
            </button>
            <button type="button" className="btn btn-secondary" onClick={cancelLinkFlow}>
              Cancel
            </button>
          </div>
        </form>
      )}

      <form className="filters-bar" onSubmit={applyFilters}>
        <label>
          Category
          <select
            value={filters.categoryId}
            onChange={(e) => setFilters({ ...filters, categoryId: e.target.value })}
          >
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c.category_id} value={c.category_id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          From
          <input
            type="date"
            value={filters.startDate}
            onChange={(e) => setFilters({ ...filters, startDate: e.target.value })}
          />
        </label>
        <label>
          To
          <input
            type="date"
            value={filters.endDate}
            onChange={(e) => setFilters({ ...filters, endDate: e.target.value })}
          />
        </label>
        <button type="submit" className="btn">Apply</button>
        <button type="button" className="btn btn-secondary" onClick={clearFilters}>Clear</button>
      </form>

      {loading && <p>Loading transactions...</p>}
      {loadError && <p className="status-banner status-error">{loadError}</p>}

      {!loading && !loadError && (
        transactions.length === 0 ? (
          <p className="empty-state">
            {appliedFilters.categoryId || appliedFilters.startDate || appliedFilters.endDate
              ? "No transactions match these filters. Try clearing them to see everything."
              : 'No transactions yet. Try "Sync bank account" or upload a receipt below.'}
          </p>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Category</th>
                  <th>Merchant</th>
                  <th>Description</th>
                  <th>Source</th>
                  <th className="amount-col">Amount</th>
                  <th className="ask-ai-col">AI</th>
                  <th className="actions-col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((t) => {
                  if (editingId === t.transaction_id) {
                    return (
                      <tr key={t.transaction_id} className="table-row-editing">
                        <td>
                          <input
                            type="date"
                            value={editForm.txnDate}
                            onChange={(e) => setEditForm({ ...editForm, txnDate: e.target.value })}
                          />
                        </td>
                        <td>
                          <input
                            type="text"
                            value={editForm.categoryName}
                            onChange={(e) => setEditForm({ ...editForm, categoryName: e.target.value })}
                            placeholder="category"
                          />
                        </td>
                        <td>
                          <input
                            type="text"
                            value={editForm.merchant}
                            onChange={(e) => setEditForm({ ...editForm, merchant: e.target.value })}
                            placeholder="merchant"
                          />
                        </td>
                        <td>
                          <input
                            type="text"
                            value={editForm.description}
                            onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                            placeholder="description"
                          />
                        </td>
                        <td>{t.source}</td>
                        <td className="amount-col">
                          <input
                            type="number"
                            step="0.01"
                            value={editForm.amount}
                            onChange={(e) => setEditForm({ ...editForm, amount: e.target.value })}
                          />
                        </td>
                        <td className="ask-ai-col" />
                        <td className="actions-col">
                          <div className="table-row-actions">
                            <button type="button" className="btn-link-ai" onClick={submitEdit} disabled={savingEdit}>
                              {savingEdit ? "Saving..." : "Save"}
                            </button>
                            <button type="button" className="btn-link-ai" onClick={cancelEdit} disabled={savingEdit}>
                              Cancel
                            </button>
                          </div>
                          {editError && <p className="status-banner status-error">{editError}</p>}
                        </td>
                      </tr>
                    );
                  }
                  return (
                    <tr key={t.transaction_id}>
                      <td>{formatDate(t.txn_date)}</td>
                      <td>{t.category_name || "uncategorised"}</td>
                      <td>{t.merchant || "-"}</td>
                      <td>{t.description || "-"}</td>
                      <td>{t.source}</td>
                      <td className={"amount-col " + (t.amount < 0 ? "amount-negative" : "amount-positive")}>
                        {t.amount < 0 ? "-" : "+"}{formatCurrency(Math.abs(t.amount))}
                      </td>
                      <td className="ask-ai-col">
                        <button
                          type="button"
                          className="btn-link-ai"
                          onClick={() => askAiAboutTransaction(t)}
                          title="Ask the AI assistant about this transaction"
                        >
                          Ask AI
                        </button>
                      </td>
                      <td className="actions-col">
                        <div className="table-row-actions">
                          <button type="button" className="btn-link-ai" onClick={() => startEdit(t)}>
                            Edit
                          </button>
                          <button
                            type="button"
                            className="btn-link-danger"
                            onClick={() => handleDeleteTransaction(t)}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )
      )}

      {!loading && !loadError && totalCount > 0 && (
        <div className="pagination-bar">
          <span className="pagination-info">
            Showing {(page - 1) * PAGE_SIZE + 1}-{Math.min(page * PAGE_SIZE, totalCount)} of {totalCount}
          </span>
          <div className="pagination-controls">
            <button
              type="button"
              className="btn btn-secondary btn-small"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              Previous
            </button>
            <span className="pagination-page">
              Page {page} of {Math.max(1, Math.ceil(totalCount / PAGE_SIZE))}
            </span>
            <button
              type="button"
              className="btn btn-secondary btn-small"
              onClick={() => setPage((p) => Math.min(Math.max(1, Math.ceil(totalCount / PAGE_SIZE)), p + 1))}
              disabled={page >= Math.ceil(totalCount / PAGE_SIZE)}
            >
              Next
            </button>
          </div>
        </div>
      )}

    </div>
  );
}

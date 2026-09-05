import { useEffect, useState } from "react";
import {
  fetchTransactionCategories,
  fetchTransactions,
  linkBankAccount,
  syncBankAccount,
  uploadReceipt,
} from "../lib/transactions";

const EMPTY_FILTERS = { categoryId: "", startDate: "", endDate: "" };

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState([]);
  const [categories, setCategories] = useState([]);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  const [linking, setLinking] = useState(false);
  const [linkMessage, setLinkMessage] = useState(null);
  const [bankLinked, setBankLinked] = useState(false);

  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState(null);

  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [uploadError, setUploadError] = useState("");

  useEffect(() => {
    setLoading(true);
    setLoadError("");
    fetchTransactions({
      categoryId: appliedFilters.categoryId || undefined,
      startDate: appliedFilters.startDate || undefined,
      endDate: appliedFilters.endDate || undefined,
    })
      .then(setTransactions)
      .catch((err) => setLoadError(err.message || "Failed to load transactions"))
      .finally(() => setLoading(false));

    // Refetch alongside transactions (not just once on mount) so newly
    // synced/uploaded categories show up in the filter dropdown too.
    fetchTransactionCategories()
      .then(setCategories)
      .catch(() => {
        // Filter dropdown just stays as-is; the transaction list load above
        // surfaces the real error to the user.
      });
  }, [appliedFilters]);

  function applyFilters(e) {
    e.preventDefault();
    setAppliedFilters(filters);
  }

  function clearFilters() {
    setFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
  }

  function reloadTransactions() {
    setAppliedFilters((prev) => ({ ...prev }));
  }

  async function handleLinkBank() {
    setLinking(true);
    setLinkMessage(null);
    try {
      await linkBankAccount();
      setBankLinked(true);
      setLinkMessage({ type: "success", text: "Bank account linked. You can now sync transactions." });
    } catch (err) {
      setLinkMessage({ type: "error", text: err.message || "Failed to link bank account" });
    } finally {
      setLinking(false);
    }
  }

  async function handleSync() {
    setSyncing(true);
    setSyncMessage(null);
    try {
      const result = await syncBankAccount();
      setSyncMessage({ type: "success", text: `Synced ${result.synced} new transaction(s).` });
      if (result.synced > 0) reloadTransactions();
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
      e.target.reset();
      reloadTransactions();
    } catch (err) {
      setUploadError(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Transactions</h1>
        <div className="page-header-actions">
          <button className="btn btn-secondary" onClick={handleLinkBank} disabled={linking || bankLinked}>
            {linking ? "Linking..." : bankLinked ? "Bank account linked" : "Link bank account"}
          </button>
          <button className="btn" onClick={handleSync} disabled={syncing}>
            {syncing ? "Syncing..." : "Sync bank account"}
          </button>
        </div>
      </div>

      <p className="empty-state">
        New here? Click "Link bank account" once to connect the demo sandbox account, then
        "Sync bank account" to pull in transactions. Already linked in an earlier session? Just
        sync.
      </p>

      {linkMessage && (
        <p className={linkMessage.type === "error" ? "status-banner status-error" : "status-banner status-success"}>
          {linkMessage.text}
        </p>
      )}

      {syncMessage && (
        <p className={syncMessage.type === "error" ? "status-banner status-error" : "status-banner status-success"}>
          {syncMessage.text}
        </p>
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
            No transactions yet. Try "Sync bank account" or upload a receipt below.
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
                </tr>
              </thead>
              <tbody>
                {transactions.map((t) => (
                  <tr key={t.transaction_id}>
                    <td>{t.txn_date}</td>
                    <td>{t.category_name || "uncategorised"}</td>
                    <td>{t.merchant || "-"}</td>
                    <td>{t.description || "-"}</td>
                    <td>{t.source}</td>
                    <td className={"amount-col " + (t.amount < 0 ? "amount-negative" : "amount-positive")}>
                      {t.amount < 0 ? "-" : "+"}${Math.abs(t.amount).toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}

      <div className="upload-card">
        <h2>Upload a receipt</h2>
        <p>We'll run OCR on it, guess the category and total, and add it as a transaction.</p>
        <form onSubmit={handleUpload}>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => setSelectedFile(e.target.files[0] || null)}
          />
          <button type="submit" className="btn" disabled={!selectedFile || uploading}>
            {uploading ? "Uploading..." : "Upload receipt"}
          </button>
        </form>

        {uploadError && <p className="status-banner status-error">{uploadError}</p>}
        {uploadResult && (
          <p className="status-banner status-success">
            Predicted category: <strong>{uploadResult.predicted_category}</strong> - predicted total:{" "}
            <strong>${uploadResult.predicted_total.toFixed(2)}</strong>
          </p>
        )}
      </div>
    </div>
  );
}

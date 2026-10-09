import { useEffect, useRef, useState } from "react";
import {
  fetchTransactionCategories,
  fetchTransactions,
  syncBankAccount,
  updateTransactionCategory,
  fetchReceiptForTransaction,
} from "../lib/transactions";
import { fetchBankAccounts } from "../lib/settings";
import BankLinkModal from "../components/BankLinkModal";
import ReceiptPreviewModal from "../components/ReceiptPreviewModal";
import AddExpenseModal from "../components/AddExpenseModal";

const EMPTY_FILTERS = { categoryId: "", startDate: "", endDate: "", search: "", source: "" };

const SOURCE_LABELS = {
  bank_sync: "Bank sync",
  receipt_ocr: "Receipt scan",
  manual: "Manual",
};

function TransactionDetailsModal({ txn, onClose }) {
  const [receipt, setReceipt] = useState(null);
  const [receiptLoading, setReceiptLoading] = useState(txn.source === "receipt_ocr");

  useEffect(() => {
    if (txn.source !== "receipt_ocr") return;
    fetchReceiptForTransaction(txn.transaction_id)
      .then(setReceipt)
      .catch(() => {})
      .finally(() => setReceiptLoading(false));
  }, [txn]);

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="Transaction details">
      <div className="modal-card">
        <div className="modal-header">
          <h2>Transaction details</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            &times;
          </button>
        </div>
        <dl className="details-list">
          <dt>Date</dt>
          <dd>{txn.txn_date}</dd>
          <dt>Merchant</dt>
          <dd>{txn.merchant || "-"}</dd>
          <dt>Category</dt>
          <dd>{txn.category_name || "uncategorised"}</dd>
          <dt>Description</dt>
          <dd>{txn.description || "-"}</dd>
          <dt>Source</dt>
          <dd>{SOURCE_LABELS[txn.source] || txn.source}</dd>
          <dt>Amount</dt>
          <dd>
            {txn.amount < 0 ? "-" : "+"}${Math.abs(txn.amount).toFixed(2)}
          </dd>
        </dl>

        {txn.source === "receipt_ocr" && (
          <div className="receipt-info-block">
            <h3 className="receipt-info-title">Receipt</h3>
            {receiptLoading && <p className="empty-state">Loading receipt...</p>}
            {!receiptLoading && !receipt && (
              <p className="empty-state">Could not load the scanned receipt for this transaction.</p>
            )}
            {!receiptLoading && receipt && (
              <>
                <p className="receipt-info-meta">
                  Scanned {receipt.processed_at ? new Date(receipt.processed_at).toLocaleString() : "-"}
                </p>
                <details className="raw-text-details">
                  <summary>Show raw scanned text</summary>
                  <pre className="raw-text-block">{receipt.ocr_raw_text}</pre>
                </details>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState([]);
  const [categories, setCategories] = useState([]);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState(null);

  const [showBankModal, setShowBankModal] = useState(false);
  const [showExpenseModal, setShowExpenseModal] = useState(false);
  const [hasLinkedAccount, setHasLinkedAccount] = useState(false);
  const [accountsLoaded, setAccountsLoaded] = useState(false);
  const [receiptFile, setReceiptFile] = useState(null);
  const fileInputRef = useRef(null);

  const [editingCategoryId, setEditingCategoryId] = useState(null);
  const [detailsTxn, setDetailsTxn] = useState(null);

  function reloadAccounts() {
    fetchBankAccounts()
      .then((accounts) => setHasLinkedAccount(accounts.length > 0))
      .catch(() => {})
      .finally(() => setAccountsLoaded(true));
  }

  useEffect(() => {
    reloadAccounts();
  }, []);

  useEffect(() => {
    setLoading(true);
    setLoadError("");
    fetchTransactions({
      categoryId: appliedFilters.categoryId || undefined,
      startDate: appliedFilters.startDate || undefined,
      endDate: appliedFilters.endDate || undefined,
      search: appliedFilters.search || undefined,
      source: appliedFilters.source || undefined,
    })
      .then(setTransactions)
      .catch((err) => setLoadError(err.message || "Failed to load transactions"))
      .finally(() => setLoading(false));

    fetchTransactionCategories()
      .then(setCategories)
      .catch(() => {});
  }, [appliedFilters]);

  function applyFilters(e) {
    e.preventDefault();
    setAppliedFilters(filters);
  }

  function setFilterAndApply(key, value) {
    const next = { ...filters, [key]: value };
    setFilters(next);
    setAppliedFilters(next);
  }

  function clearFilters() {
    setFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
  }

  function reloadTransactions() {
    setAppliedFilters((prev) => ({ ...prev }));
  }

  async function handleSync() {
    setSyncing(true);
    setSyncMessage(null);
    try {
      const result = await syncBankAccount();
      setSyncMessage({ type: "success", text: `Synced ${result.synced} new transaction(s).` });
      if (result.synced > 0) reloadTransactions();
    } catch (err) {
      setSyncMessage({ type: "error", text: err.message || "Sync failed. Have you linked a bank account yet?" });
    } finally {
      setSyncing(false);
    }
  }

  function handleFilePicked(e) {
    const file = e.target.files[0];
    if (file) setReceiptFile(file);
    e.target.value = "";
  }

  async function handleCategoryChange(transactionId, newCategory) {
    if (!newCategory.trim()) return;
    try {
      await updateTransactionCategory(transactionId, newCategory.trim());
      reloadTransactions();
    } finally {
      setEditingCategoryId(null);
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Transactions</h1>
        <div className="page-header-actions">
          <button
            className="btn btn-secondary"
            onClick={() => setShowBankModal(true)}
            disabled={!accountsLoaded || hasLinkedAccount}
            title={hasLinkedAccount ? "Disconnect your current account in Settings before linking another" : undefined}
          >
            {hasLinkedAccount ? "Bank account linked" : "Link bank account"}
          </button>
          <button className="btn btn-secondary" onClick={handleSync} disabled={syncing}>
            {syncing ? "Syncing..." : "Sync bank account"}
          </button>
          <button className="btn btn-secondary" onClick={() => fileInputRef.current?.click()}>
            Scan receipt
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFilePicked}
            style={{ display: "none" }}
          />
          <button className="btn" onClick={() => setShowExpenseModal(true)}>
            + Add transaction
          </button>
        </div>
      </div>

      {syncMessage && (
        <p className={syncMessage.type === "error" ? "status-banner status-error" : "status-banner status-success"}>
          {syncMessage.text}
        </p>
      )}

      <form className="filters-bar" onSubmit={applyFilters}>
        <label>
          Search merchant
          <input
            type="text"
            value={filters.search}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            placeholder="e.g. Woolworths"
          />
        </label>
        <label>
          Category
          <select
            value={filters.categoryId}
            onChange={(e) => setFilterAndApply("categoryId", e.target.value)}
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
          Source
          <select
            value={filters.source}
            onChange={(e) => setFilterAndApply("source", e.target.value)}
          >
            <option value="">All sources</option>
            <option value="bank_sync">Bank sync</option>
            <option value="receipt_ocr">Receipt scan</option>
            <option value="manual">Manual</option>
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
            No transactions yet. Link a bank account and sync, scan a receipt, or add an expense manually.
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
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((t) => (
                  <tr key={t.transaction_id}>
                    <td>{t.txn_date}</td>
                    <td>
                      {editingCategoryId === t.transaction_id ? (
                        <input
                          type="text"
                          autoFocus
                          defaultValue={t.category_name || ""}
                          className="inline-category-input"
                          onBlur={(e) => handleCategoryChange(t.transaction_id, e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") e.target.blur();
                            if (e.key === "Escape") setEditingCategoryId(null);
                          }}
                        />
                      ) : (
                        <button
                          className="category-edit-chip"
                          onClick={() => setEditingCategoryId(t.transaction_id)}
                          title="Click to edit category"
                        >
                          {t.category_name || "uncategorised"}
                        </button>
                      )}
                    </td>
                    <td>{t.merchant || "-"}</td>
                    <td>{t.description || "-"}</td>
                    <td>{SOURCE_LABELS[t.source] || t.source}</td>
                    <td className={"amount-col " + (t.amount < 0 ? "amount-negative" : "amount-positive")}>
                      {t.amount < 0 ? "-" : "+"}${Math.abs(t.amount).toFixed(2)}
                    </td>
                    <td>
                      <button className="btn-link" onClick={() => setDetailsTxn(t)}>
                        Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}

      {showBankModal && (
        <BankLinkModal onClose={() => setShowBankModal(false)} onConnected={reloadAccounts} />
      )}

      {receiptFile && (
        <ReceiptPreviewModal
          file={receiptFile}
          onClose={() => setReceiptFile(null)}
          onConfirmed={() => reloadTransactions()}
        />
      )}

      {showExpenseModal && (
        <AddExpenseModal
          onClose={() => setShowExpenseModal(false)}
          onCreated={() => reloadTransactions()}
        />
      )}

      {detailsTxn && <TransactionDetailsModal txn={detailsTxn} onClose={() => setDetailsTxn(null)} />}
    </div>
  );
}

import { useEffect, useState } from "react";
import { uploadReceipt, confirmReceipt } from "../lib/transactions";

const CATEGORY_SUGGESTIONS = [
  "groceries",
  "dining",
  "utilities",
  "transport",
  "entertainment",
  "health",
  "shopping",
  "subscriptions",
  "uncategorised",
];

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

export default function ReceiptPreviewModal({ file, onClose, onConfirmed }) {
  const [stage, setStage] = useState("scanning"); // scanning | preview | confirming | error
  const [error, setError] = useState("");
  const [receiptId, setReceiptId] = useState(null);
  const [rawText, setRawText] = useState("");
  const [merchant, setMerchant] = useState("");
  const [total, setTotal] = useState("");
  const [category, setCategory] = useState("");
  const [txnDate, setTxnDate] = useState(todayStr());

  useEffect(() => {
    let cancelled = false;
    setStage("scanning");
    setError("");
    uploadReceipt(file)
      .then((preview) => {
        if (cancelled) return;
        setReceiptId(preview.receipt_id);
        setRawText(preview.raw_text);
        setMerchant(preview.predicted_merchant || "");
        setTotal(preview.predicted_total != null ? String(preview.predicted_total) : "");
        setCategory(preview.predicted_category || "uncategorised");
        setTxnDate(preview.predicted_date || todayStr());
        setStage("preview");
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message || "Could not scan this receipt.");
        setStage("error");
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [file]);

  async function handleConfirm(e) {
    e.preventDefault();
    const parsedTotal = parseFloat(total);
    if (!parsedTotal || parsedTotal <= 0) {
      setError("Enter a total greater than $0.");
      return;
    }
    if (!category.trim()) {
      setError("Enter a category.");
      return;
    }

    setStage("confirming");
    setError("");
    try {
      const result = await confirmReceipt(receiptId, {
        total: parsedTotal,
        category_name: category.trim(),
        merchant: merchant.trim() || null,
        txn_date: txnDate,
      });
      onConfirmed(result);
      onClose();
    } catch (err) {
      setError(err.message || "Could not save this transaction.");
      setStage("preview");
    }
  }

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="Upload a receipt">
      <div className="modal-card">
        <div className="modal-header">
          <h2>Scan receipt</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            &times;
          </button>
        </div>

        {stage === "scanning" && (
          <div className="bank-wizard-step wizard-center">
            <div className="spinner" aria-hidden="true" />
            <p>Analysing receipt&hellip;</p>
          </div>
        )}

        {stage === "error" && (
          <div className="bank-wizard-step">
            <p className="status-banner status-error">{error}</p>
            <button className="btn btn-secondary" onClick={onClose}>
              Close
            </button>
          </div>
        )}

        {(stage === "preview" || stage === "confirming") && (
          <form className="receipt-preview-form" onSubmit={handleConfirm}>
            <p className="wizard-step-label">Review the extracted details, then confirm</p>

            {error && <p className="status-banner status-error">{error}</p>}

            <label>
              Merchant
              <input
                type="text"
                value={merchant}
                onChange={(e) => setMerchant(e.target.value)}
                placeholder="e.g. Woolworths"
              />
            </label>

            <div className="receipt-form-row">
              <label>
                Total ($)
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={total}
                  onChange={(e) => setTotal(e.target.value)}
                  required
                />
              </label>
              <label>
                Date
                <input
                  type="date"
                  value={txnDate}
                  onChange={(e) => setTxnDate(e.target.value)}
                  required
                />
              </label>
            </div>

            <label>
              Category
              <input
                type="text"
                list="receipt-category-options"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                required
              />
              <datalist id="receipt-category-options">
                {CATEGORY_SUGGESTIONS.map((c) => (
                  <option key={c} value={c} />
                ))}
              </datalist>
            </label>

            <details className="raw-text-details">
              <summary>Show raw scanned text</summary>
              <pre className="raw-text-block">{rawText}</pre>
            </details>

            <div className="wizard-actions">
              <button type="button" className="btn btn-secondary" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="btn" disabled={stage === "confirming"}>
                {stage === "confirming" ? "Saving..." : "Confirm transaction"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

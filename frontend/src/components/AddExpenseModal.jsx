import { useState } from "react";
import { createTransaction } from "../lib/transactions";

const CATEGORY_SUGGESTIONS = [
  "groceries",
  "dining",
  "utilities",
  "transport",
  "entertainment",
  "health",
  "shopping",
  "subscriptions",
  "income",
];

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

export default function AddExpenseModal({ onClose, onCreated }) {
  const [type, setType] = useState("expense"); // expense | income
  const [amount, setAmount] = useState("");
  const [merchant, setMerchant] = useState("");
  const [category, setCategory] = useState("");
  const [txnDate, setTxnDate] = useState(todayStr());
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    const parsed = parseFloat(amount);
    if (!parsed || parsed <= 0) {
      setError("Enter an amount greater than $0.");
      return;
    }

    setSaving(true);
    setError("");
    try {
      const result = await createTransaction({
        amount: type === "expense" ? -parsed : parsed,
        txn_date: txnDate,
        category_name: category.trim() || null,
        merchant: merchant.trim() || null,
        description: description.trim() || null,
      });
      onCreated(result);
      onClose();
    } catch (err) {
      setError(err.message || "Could not save this expense.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-label={type === "income" ? "Add income" : "Add an expense"}
    >
      <div className="modal-card">
        <div className="modal-header">
          <h2>{type === "income" ? "Add income" : "Add expense"}</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            &times;
          </button>
        </div>

        <form className="receipt-preview-form" onSubmit={handleSubmit}>
          {error && <p className="status-banner status-error">{error}</p>}

          <div className="type-toggle">
            <button
              type="button"
              className={"type-toggle-option" + (type === "expense" ? " active" : "")}
              onClick={() => setType("expense")}
            >
              Expense
            </button>
            <button
              type="button"
              className={"type-toggle-option" + (type === "income" ? " active" : "")}
              onClick={() => setType("income")}
            >
              Income
            </button>
          </div>

          <div className="receipt-form-row">
            <label>
              Amount ($)
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                required
                autoFocus
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
            Merchant / payee
            <input
              type="text"
              value={merchant}
              onChange={(e) => setMerchant(e.target.value)}
              placeholder="e.g. Local Cafe"
            />
          </label>

          <label>
            Category
            <input
              type="text"
              list="expense-category-options"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="e.g. dining"
            />
            <datalist id="expense-category-options">
              {CATEGORY_SUGGESTIONS.map((c) => (
                <option key={c} value={c} />
              ))}
            </datalist>
          </label>

          <label>
            Note (optional)
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Team lunch"
            />
          </label>

          <div className="wizard-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn" disabled={saving}>
              {saving ? "Saving..." : type === "income" ? "Add income" : "Add expense"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

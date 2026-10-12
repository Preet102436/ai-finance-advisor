import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LabelList,
} from "recharts";
import { fetchTransactions } from "../lib/transactions";
import {
  fetchBudgets,
  recommendBudgets,
  generateForecast,
  detectAnomalies,
  createBudget,
  updateBudget,
  deleteBudget,
} from "../lib/dashboard";
import SavingsSuggestionsPanel from "../components/SavingsSuggestionsPanel";
import FinancialSummaryCards from "../components/FinancialSummaryCards";

// From the dataviz skill's reference palette (references/palette.md) -
// sequential blue for magnitude, status colors reserved for severity only.
// These reference the app's CSS custom properties (defined in index.css)
// rather than literal hex values, so the chart repaints correctly when the
// person switches between light and dark mode - modern browsers resolve
// var(...) in SVG fill/stroke attributes just like any other CSS color.
const COLORS = {
  seriesBlue: "#2a78d6",
  gridline: "var(--color-border)",
  axisLine: "var(--color-text-faint)",
  textMuted: "var(--color-text-muted)",
  textSecondary: "var(--color-text-muted)",
  textPrimary: "var(--color-text)",
  surface: "var(--color-card-bg)",
  good: "var(--color-success-text)",
  warning: "var(--color-warning-text)",
  critical: "var(--color-error-text)",
};

function firstOfMonth() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
}

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

function severityFor(ratio) {
  if (ratio >= 1) return "critical";
  if (ratio >= 0.8) return "warning";
  return "good";
}

const SEVERITY_LABEL = { good: "On track", warning: "Near limit", critical: "Over budget" };

function SettingsGearIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="M12 3V5.2M12 18.8V21M21 12H18.8M5.2 12H3M18.0 6.0L16.5 7.5M7.5 16.5L6.0 18.0M18.0 18.0L16.5 16.5M7.5 7.5L6.0 6.0"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

function BudgetMeter({ budgetId, label, actual, budget, onChangeBudget, onDeleteBudget }) {
  const ratio = budget > 0 ? actual / budget : 0;
  const severity = severityFor(ratio);
  const widthPct = Math.min(ratio, 1) * 100;

  const [menuOpen, setMenuOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [amountInput, setAmountInput] = useState(String(budget));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function applyDelta(delta) {
    setSaving(true);
    setError("");
    try {
      await onChangeBudget(budgetId, Math.max(1, Math.round((budget + delta) * 100) / 100));
    } catch (err) {
      setError(err.message || "Failed to update budget");
    } finally {
      setSaving(false);
    }
  }

  async function applyCustomAmount(e) {
    e.preventDefault();
    const amt = parseFloat(amountInput);
    if (Number.isNaN(amt) || amt <= 0) {
      setError("Enter an amount greater than 0.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await onChangeBudget(budgetId, amt);
      setEditing(false);
    } catch (err) {
      setError(err.message || "Failed to update budget");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="budget-card">
      <div className="budget-card-header">
        <span className="budget-card-category">{label}</span>
        <div className="budget-card-header-right">
          <span className={`budget-card-status budget-card-status-${severity}`}>
            {SEVERITY_LABEL[severity]}
          </span>
          <div className="card-menu-wrap">
            <button
              type="button"
              className="card-menu-trigger"
              onClick={() => setMenuOpen((v) => !v)}
              aria-label="Budget settings"
              title="Increase, decrease or delete this budget"
            >
              <SettingsGearIcon />
            </button>
            {menuOpen && (
              <div className="card-menu">
                <button type="button" disabled={saving} onClick={() => { setMenuOpen(false); applyDelta(10); }}>
                  Increase by $10
                </button>
                <button type="button" disabled={saving} onClick={() => { setMenuOpen(false); applyDelta(-10); }}>
                  Decrease by $10
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setMenuOpen(false);
                    setAmountInput(String(budget));
                    setEditing(true);
                  }}
                >
                  Set custom amount
                </button>
                <button
                  type="button"
                  className="card-menu-danger"
                  onClick={() => {
                    setMenuOpen(false);
                    onDeleteBudget(budgetId);
                  }}
                >
                  Delete budget
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
      <div className="meter-track">
        <div className="meter-fill" style={{ width: `${widthPct}%`, background: COLORS[severity] }} />
      </div>
      <div className="budget-card-amounts">
        <span>${actual.toFixed(2)} spent</span>
        <span className="budget-card-limit">of ${budget.toFixed(2)} budget</span>
      </div>
      {editing && (
        <form className="card-inline-form" onSubmit={applyCustomAmount}>
          <div className="card-inline-form-row">
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={amountInput}
              onChange={(e) => setAmountInput(e.target.value)}
            />
            <button type="submit" className="btn btn-small" disabled={saving}>
              Save
            </button>
            <button type="button" className="btn btn-secondary btn-small" onClick={() => setEditing(false)}>
              Cancel
            </button>
          </div>
        </form>
      )}
      {error && <p className="status-banner status-error">{error}</p>}
    </div>
  );
}

export default function DashboardPage() {
  const [budgets, setBudgets] = useState([]);
  const [budgetsLoading, setBudgetsLoading] = useState(true);
  const [budgetsError, setBudgetsError] = useState("");

  const [showNewBudgetForm, setShowNewBudgetForm] = useState(false);
  const [newBudget, setNewBudget] = useState({ categoryName: "", amount: "" });
  const [creatingBudget, setCreatingBudget] = useState(false);
  const [newBudgetError, setNewBudgetError] = useState("");

  const [actualByCategory, setActualByCategory] = useState({});
  const [spendLoading, setSpendLoading] = useState(true);
  const [spendError, setSpendError] = useState("");

  const [forecast, setForecast] = useState(null);
  const [forecastLoading, setForecastLoading] = useState(true);
  const [forecastError, setForecastError] = useState("");

  const [anomalies, setAnomalies] = useState([]);
  const [anomaliesLoading, setAnomaliesLoading] = useState(true);
  const [anomaliesError, setAnomaliesError] = useState("");

  useEffect(() => {
    // Load whatever budgets already exist for this month first - this is
    // the source of truth and reflects every edit/delete exactly as the
    // user left it. Only fall back to auto-recommending from trailing
    // spend when there's nothing at all yet, so simply revisiting the
    // Dashboard never overwrites an edited amount or brings back a
    // budget the user deleted.
    fetchBudgets()
      .then((existing) =>
        existing.length > 0 ? existing : recommendBudgets().catch(() => []).then(fetchBudgets)
      )
      .then(setBudgets)
      .catch((err) => setBudgetsError(err.message || "Failed to load budgets"))
      .finally(() => setBudgetsLoading(false));

    fetchTransactions({ startDate: firstOfMonth(), endDate: todayStr() })
      .then((txns) => {
        const totals = {};
        for (const t of txns) {
          if (t.amount >= 0) continue;
          const key = t.category_name || "uncategorised";
          totals[key] = (totals[key] || 0) + Math.abs(t.amount);
        }
        setActualByCategory(totals);
      })
      .catch((err) => setSpendError(err.message || "Failed to load spending"))
      .finally(() => setSpendLoading(false));

    generateForecast({ daysAhead: 14 })
      .then(setForecast)
      .catch((err) => setForecastError(err.message || "Failed to load forecast"))
      .finally(() => setForecastLoading(false));

    detectAnomalies()
      .then(setAnomalies)
      .catch((err) => setAnomaliesError(err.message || "Failed to load anomalies"))
      .finally(() => setAnomaliesLoading(false));
  }, []);

  async function handleChangeBudget(budgetId, amount) {
    const updated = await updateBudget(budgetId, amount);
    setBudgets((prev) => prev.map((b) => (b.budget_id === budgetId ? updated : b)));
  }

  async function handleDeleteBudget(budgetId) {
    const ok = window.confirm("Delete this budget? You can always create a new one for this category later.");
    if (!ok) return;
    try {
      await deleteBudget(budgetId);
      setBudgets((prev) => prev.filter((b) => b.budget_id !== budgetId));
    } catch (err) {
      setBudgetsError(err.message || "Failed to delete budget");
    }
  }

  async function handleCreateBudget(e) {
    e.preventDefault();
    const amount = parseFloat(newBudget.amount);
    if (!newBudget.categoryName.trim()) {
      setNewBudgetError("Enter a category name.");
      return;
    }
    if (Number.isNaN(amount) || amount <= 0) {
      setNewBudgetError("Enter an amount greater than 0.");
      return;
    }
    setCreatingBudget(true);
    setNewBudgetError("");
    try {
      const created = await createBudget({ categoryName: newBudget.categoryName.trim(), amount });
      setBudgets((prev) => [...prev.filter((b) => b.budget_id !== created.budget_id), created]);
      setNewBudget({ categoryName: "", amount: "" });
      setShowNewBudgetForm(false);
    } catch (err) {
      setNewBudgetError(err.message || "Failed to create budget");
    } finally {
      setCreatingBudget(false);
    }
  }

  const forecastData = forecast
    ? forecast.forecast.map((p) => ({
        date: p.forecast_date,
        predicted: p.predicted_balance,
        range:
          p.lower_bound != null && p.upper_bound != null ? [p.lower_bound, p.upper_bound] : undefined,
      }))
    : [];
  const hasConfidenceBand = forecastData.some((p) => p.range);

  const categoryData = Object.entries(actualByCategory)
    .map(([name, amount]) => ({ name, amount: Math.round(amount * 100) / 100 }))
    .sort((a, b) => b.amount - a.amount);

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
      </div>

      <section className="dashboard-section">
        <FinancialSummaryCards />
      </section>

      <section className="dashboard-section">
        <div className="section-title-row">
          <h2 className="section-title">Budget vs actual this month</h2>
          <button
            type="button"
            className="btn btn-secondary btn-small"
            onClick={() => setShowNewBudgetForm((v) => !v)}
          >
            {showNewBudgetForm ? "Cancel" : "+ New budget"}
          </button>
        </div>
        {showNewBudgetForm && (
          <form className="add-transaction-card new-budget-card" onSubmit={handleCreateBudget}>
            <div className="form-row">
              <label>
                Category
                <input
                  type="text"
                  value={newBudget.categoryName}
                  onChange={(e) => setNewBudget({ ...newBudget, categoryName: e.target.value })}
                  placeholder="e.g. entertainment"
                  required
                />
              </label>
              <label>
                Monthly budget amount
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={newBudget.amount}
                  onChange={(e) => setNewBudget({ ...newBudget, amount: e.target.value })}
                  placeholder="200.00"
                  required
                />
              </label>
            </div>
            <span className="field-hint">
              Works for a brand-new category too - it'll show up here with $0 spent until you
              have transactions in it.
            </span>
            {newBudgetError && <p className="status-banner status-error">{newBudgetError}</p>}
            <button type="submit" className="btn" disabled={creatingBudget}>
              {creatingBudget ? "Creating..." : "Create budget"}
            </button>
          </form>
        )}
        {budgetsLoading && <p>Loading budgets...</p>}
        {budgetsError && <p className="status-banner status-error">{budgetsError}</p>}
        {!budgetsLoading && !budgetsError && (
          budgets.length === 0 ? (
            <p className="empty-state">
              No budget recommendations yet. Sync a few months of transactions on the Transactions
              page, then check back here, or create a budget of your own above.
            </p>
          ) : (
            <div className="cards-grid">
              {budgets.map((b) => (
                <BudgetMeter
                  key={b.budget_id}
                  budgetId={b.budget_id}
                  label={b.category_name}
                  actual={actualByCategory[b.category_name] || 0}
                  budget={b.recommended_amount}
                  onChangeBudget={handleChangeBudget}
                  onDeleteBudget={handleDeleteBudget}
                />
              ))}
            </div>
          )
        )}
      </section>

      <section className="dashboard-section">
        <SavingsSuggestionsPanel title="Savings suggestions" />
      </section>

      <section className="dashboard-section">
        <h2 className="section-title">Balance forecast</h2>
        {forecastLoading && <p>Loading forecast...</p>}
        {forecastError && forecastError !== "No linked bank account found" && (
          <p className="status-banner status-error">{forecastError}</p>
        )}
        {forecastError === "No linked bank account found" && (
          <p className="empty-state">
            Link a bank account (or add some manual transactions) to see your balance forecast.
          </p>
        )}
        {!forecastLoading && !forecastError && forecast && (
          <div className="chart-card">
            <p className="chart-subtitle">
              Next {forecast.days_ahead} days - method:{" "}
              {forecast.method === "prophet" ? "Prophet" : "moving average"}
              {!hasConfidenceBand && " (no confidence interval for this method)"}
            </p>
            <div className="chart-legend">
              <span className="legend-item">
                <span className="legend-swatch legend-line" /> Predicted balance
              </span>
              {hasConfidenceBand && (
                <span className="legend-item">
                  <span className="legend-swatch legend-area" /> Confidence range
                </span>
              )}
            </div>
            <ResponsiveContainer width="100%" height={280}>
              <ComposedChart data={forecastData} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                <CartesianGrid stroke={COLORS.gridline} vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fill: COLORS.textMuted, fontSize: 12 }}
                  axisLine={{ stroke: COLORS.axisLine }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: COLORS.textMuted, fontSize: 12 }}
                  axisLine={{ stroke: COLORS.axisLine }}
                  tickLine={false}
                  tickFormatter={(v) => `$${Math.round(v).toLocaleString()}`}
                  width={70}
                />
                <Tooltip
                  formatter={(value, name) => {
                    if (name === "range" && Array.isArray(value)) {
                      return [`$${value[0].toFixed(2)} - $${value[1].toFixed(2)}`, "Confidence range"];
                    }
                    return [`$${Number(value).toFixed(2)}`, "Predicted balance"];
                  }}
                  contentStyle={{ borderRadius: 8, border: `1px solid ${COLORS.gridline}`, fontSize: 13 }}
                />
                {hasConfidenceBand && (
                  <Area
                    dataKey="range"
                    stroke="none"
                    fill={COLORS.seriesBlue}
                    fillOpacity={0.1}
                    isAnimationActive={false}
                  />
                )}
                <Line
                  type="monotone"
                  dataKey="predicted"
                  stroke={COLORS.seriesBlue}
                  strokeWidth={2}
                  dot={{ r: 4, fill: COLORS.seriesBlue, stroke: COLORS.surface, strokeWidth: 2 }}
                  isAnimationActive={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      <section className="dashboard-section">
        <h2 className="section-title">Spending by category</h2>
        {spendLoading && <p>Loading spending...</p>}
        {spendError && <p className="status-banner status-error">{spendError}</p>}
        {!spendLoading && !spendError && (
          categoryData.length === 0 ? (
            <p className="empty-state">No spending recorded this month yet.</p>
          ) : (
            <div className="chart-card">
              <ResponsiveContainer width="100%" height={Math.max(180, categoryData.length * 44)}>
                <BarChart data={categoryData} layout="vertical" margin={{ top: 8, right: 40, left: 8, bottom: 8 }}>
                  <CartesianGrid stroke={COLORS.gridline} horizontal={false} />
                  <XAxis
                    type="number"
                    tick={{ fill: COLORS.textMuted, fontSize: 12 }}
                    axisLine={{ stroke: COLORS.axisLine }}
                    tickLine={false}
                    tickFormatter={(v) => `$${v}`}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    tick={{ fill: COLORS.textPrimary, fontSize: 13 }}
                    axisLine={false}
                    tickLine={false}
                    width={110}
                  />
                  <Tooltip
                    formatter={(value) => [`$${Number(value).toFixed(2)}`, "Spent"]}
                    contentStyle={{ borderRadius: 8, border: `1px solid ${COLORS.gridline}`, fontSize: 13 }}
                  />
                  <Bar dataKey="amount" fill={COLORS.seriesBlue} radius={[0, 4, 4, 0]} maxBarSize={24}>
                    <LabelList
                      dataKey="amount"
                      position="right"
                      formatter={(v) => `$${Number(v).toFixed(0)}`}
                      fill={COLORS.textSecondary}
                      fontSize={12}
                    />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )
        )}
      </section>

      <section className="dashboard-section">
        <h2 className="section-title">Flagged anomalies</h2>
        {anomaliesLoading && <p>Loading anomalies...</p>}
        {anomaliesError && <p className="status-banner status-error">{anomaliesError}</p>}
        {!anomaliesLoading && !anomaliesError && (
          anomalies.length === 0 ? (
            <p className="empty-state">No unusual transactions flagged.</p>
          ) : (
            <ul className="anomaly-list">
              {anomalies.map((a) => (
                <li key={a.anomaly_id} className="anomaly-item">
                  <div className="anomaly-main">
                    <span className="anomaly-category">{a.category_name}</span>
                    <span className="anomaly-merchant">{a.merchant || "-"}</span>
                    <span className="anomaly-date">{a.txn_date}</span>
                  </div>
                  <div className="anomaly-side">
                    <span className="anomaly-amount">${Math.abs(a.amount).toFixed(2)}</span>
                    <span className="anomaly-badge">z={a.z_score.toFixed(2)}</span>
                  </div>
                </li>
              ))}
            </ul>
          )
        )}
      </section>
    </div>
  );
}

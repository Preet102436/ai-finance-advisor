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
  recommendBudgets,
  fetchBudgets,
  createOrUpdateBudget,
  updateBudget,
  generateForecast,
  detectAnomalies,
  fetchInsights,
} from "../lib/dashboard";
import SavingsSuggestionsPanel from "../components/SavingsSuggestionsPanel";
import OnboardingChecklist from "../components/OnboardingChecklist";

// From the dataviz skill's reference palette (references/palette.md) -
// sequential accent for magnitude, status colors reserved for severity only.
const COLORS = {
  seriesBlue: "#017a5c",
  gridline: "#e1e0d9",
  axisLine: "#c3c2b7",
  textMuted: "#898781",
  textSecondary: "#52514e",
  textPrimary: "#0b0b0b",
  surface: "#fcfcfb",
  good: "#0ca30c",
  warning: "#fab219",
  critical: "#d03b3b",
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

function BudgetMeter({ budget, actual, onSave }) {
  const [editing, setEditing] = useState(false);
  const [amount, setAmount] = useState(String(budget.recommended_amount));
  const [saving, setSaving] = useState(false);

  const ratio = budget.recommended_amount > 0 ? actual / budget.recommended_amount : 0;
  const severity = severityFor(ratio);
  const widthPct = Math.min(ratio, 1) * 100;

  async function handleSave() {
    const parsed = parseFloat(amount);
    if (!parsed || parsed <= 0) return;
    setSaving(true);
    try {
      await onSave(budget.budget_id, parsed);
      setEditing(false);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="budget-card">
      <div className="budget-card-header">
        <span className="budget-card-category">{budget.category_name}</span>
        <span className={`budget-card-status budget-card-status-${severity}`}>
          {SEVERITY_LABEL[severity]}
        </span>
      </div>
      <div className="meter-track">
        <div className="meter-fill" style={{ width: `${widthPct}%`, background: COLORS[severity] }} />
      </div>
      <div className="budget-card-amounts">
        <span>${actual.toFixed(2)} spent</span>
        <span className="budget-card-limit">
          of{" "}
          {editing ? (
            <input
              type="number"
              step="0.01"
              min="0.01"
              className="budget-edit-input"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              autoFocus
            />
          ) : (
            `$${budget.recommended_amount.toFixed(2)}`
          )}{" "}
          budget
        </span>
      </div>
      {editing ? (
        <div className="budget-edit-actions">
          <button className="btn-link" onClick={() => setEditing(false)} disabled={saving}>
            Cancel
          </button>
          <button className="btn-link" onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      ) : (
        <button className="btn-link budget-edit-trigger" onClick={() => setEditing(true)}>
          Edit budget
        </button>
      )}
    </div>
  );
}

function AddBudgetForm({ onAdd, onCancel }) {
  const [category, setCategory] = useState("");
  const [amount, setAmount] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    const parsed = parseFloat(amount);
    if (!category.trim() || !parsed || parsed <= 0) return;
    setSaving(true);
    try {
      await onAdd(category.trim(), parsed);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="budget-card add-budget-card" onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Category (e.g. dining)"
        value={category}
        onChange={(e) => setCategory(e.target.value)}
        autoFocus
      />
      <input
        type="number"
        step="0.01"
        min="0.01"
        placeholder="Monthly budget ($)"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
      />
      <div className="budget-edit-actions">
        <button type="button" className="btn-link" onClick={onCancel} disabled={saving}>
          Cancel
        </button>
        <button type="submit" className="btn-link" disabled={saving}>
          {saving ? "Saving..." : "Add"}
        </button>
      </div>
    </form>
  );
}

function SummaryCard({ label, value, tone, icon }) {
  return (
    <div className={"summary-card" + (tone ? ` summary-card-${tone}` : "")}>
      <span className="summary-card-icon" aria-hidden="true">
        {icon}
      </span>
      <span className="summary-card-label">{label}</span>
      <span className="summary-card-value">{value}</span>
    </div>
  );
}

function InsightsPanel({ insights, loading, error }) {
  return (
    <section className="dashboard-section">
      <h2 className="section-title">AI insights</h2>
      {loading && <p>Analysing your spending...</p>}
      {error && <p className="status-banner status-error">{error}</p>}
      {!loading && !error && (
        insights.length === 0 ? (
          <p className="empty-state">
            Not enough history yet for insights - sync more transactions or wait a few days.
          </p>
        ) : (
          <ul className="insight-list">
            {insights.map((insight, i) => (
              <li key={i} className={`insight-item insight-${insight.severity}`}>
                {insight.message}
              </li>
            ))}
          </ul>
        )
      )}
    </section>
  );
}

export default function DashboardPage() {
  const [budgets, setBudgets] = useState([]);
  const [budgetsLoading, setBudgetsLoading] = useState(true);
  const [budgetsError, setBudgetsError] = useState("");
  const [showAddBudget, setShowAddBudget] = useState(false);

  const [monthTxns, setMonthTxns] = useState([]);
  const [spendLoading, setSpendLoading] = useState(true);
  const [spendError, setSpendError] = useState("");

  const [allTxns, setAllTxns] = useState([]);

  const [forecast, setForecast] = useState(null);
  const [forecastLoading, setForecastLoading] = useState(true);
  const [forecastError, setForecastError] = useState("");

  const [anomalies, setAnomalies] = useState([]);
  const [anomaliesLoading, setAnomaliesLoading] = useState(true);
  const [anomaliesError, setAnomaliesError] = useState("");

  const [insights, setInsights] = useState([]);
  const [insightsLoading, setInsightsLoading] = useState(true);
  const [insightsError, setInsightsError] = useState("");

  function reloadBudgets() {
    setBudgetsLoading(true);
    return fetchBudgets()
      .then(setBudgets)
      .catch((err) => setBudgetsError(err.message || "Failed to load budgets"))
      .finally(() => setBudgetsLoading(false));
  }

  useEffect(() => {
    recommendBudgets()
      .catch(() => {})
      .finally(reloadBudgets);

    fetchTransactions({ startDate: firstOfMonth(), endDate: todayStr() })
      .then(setMonthTxns)
      .catch((err) => setSpendError(err.message || "Failed to load spending"))
      .finally(() => setSpendLoading(false));

    fetchTransactions()
      .then(setAllTxns)
      .catch(() => {});

    generateForecast({ daysAhead: 14 })
      .then(setForecast)
      .catch((err) => setForecastError(err.message || "Failed to load forecast"))
      .finally(() => setForecastLoading(false));

    detectAnomalies()
      .then(setAnomalies)
      .catch((err) => setAnomaliesError(err.message || "Failed to load anomalies"))
      .finally(() => setAnomaliesLoading(false));

    fetchInsights()
      .then(setInsights)
      .catch((err) => setInsightsError(err.message || "Failed to load insights"))
      .finally(() => setInsightsLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleBudgetSave(budgetId, amount) {
    await updateBudget(budgetId, amount);
    await reloadBudgets();
  }

  async function handleBudgetAdd(categoryName, amount) {
    await createOrUpdateBudget({ categoryName, amount });
    setShowAddBudget(false);
    await reloadBudgets();
  }

  const actualByCategory = {};
  for (const t of monthTxns) {
    if (t.amount >= 0) continue;
    const key = t.category_name || "uncategorised";
    actualByCategory[key] = (actualByCategory[key] || 0) + Math.abs(t.amount);
  }

  const monthIncome = monthTxns.filter((t) => t.amount > 0).reduce((s, t) => s + t.amount, 0);
  const monthExpenses = monthTxns.filter((t) => t.amount < 0).reduce((s, t) => s + Math.abs(t.amount), 0);
  const monthSavings = monthIncome - monthExpenses;
  const balance = allTxns.reduce((s, t) => s + t.amount, 0);
  const totalBudget = budgets.reduce((s, b) => s + b.recommended_amount, 0);
  const totalBudgetSpent = budgets.reduce((s, b) => s + (actualByCategory[b.category_name] || 0), 0);
  const budgetUsedPct = totalBudget > 0 ? Math.min((totalBudgetSpent / totalBudget) * 100, 999) : null;

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

      {!spendLoading && allTxns.length === 0 && (
        <OnboardingChecklist hasTransactions={allTxns.length > 0} hasBudgets={budgets.length > 0} />
      )}

      <section className="dashboard-section">
        <div className="summary-cards-row">
          <SummaryCard icon="💰" label="Balance" value={`$${balance.toFixed(2)}`} />
          <SummaryCard icon="📈" label="Income (month)" value={`$${monthIncome.toFixed(2)}`} tone="good" />
          <SummaryCard icon="📉" label="Expenses (month)" value={`$${monthExpenses.toFixed(2)}`} tone="critical" />
          <SummaryCard
            icon="🏦"
            label="Savings (month)"
            value={`${monthSavings < 0 ? "-" : ""}$${Math.abs(monthSavings).toFixed(2)}`}
            tone={monthSavings >= 0 ? "good" : "critical"}
          />
          <SummaryCard
            icon="📊"
            label="Budget used"
            value={budgetUsedPct == null ? "-" : `${budgetUsedPct.toFixed(0)}%`}
            tone={budgetUsedPct != null && budgetUsedPct >= 100 ? "critical" : budgetUsedPct != null && budgetUsedPct >= 80 ? "warning" : undefined}
          />
        </div>
      </section>

      <InsightsPanel insights={insights} loading={insightsLoading} error={insightsError} />

      <section className="dashboard-section">
        <div className="section-title-row">
          <h2 className="section-title">Budget vs actual this month</h2>
          {!showAddBudget && (
            <button className="btn btn-secondary btn-sm" onClick={() => setShowAddBudget(true)}>
              + Add budget
            </button>
          )}
        </div>
        {budgetsLoading && <p>Generating budgets...</p>}
        {budgetsError && <p className="status-banner status-error">{budgetsError}</p>}
        {!budgetsLoading && !budgetsError && (
          budgets.length === 0 && !showAddBudget ? (
            <p className="empty-state">
              No budgets yet. Sync a few months of transactions for AI recommendations, or add one
              manually above.
            </p>
          ) : (
            <div className="cards-grid">
              {budgets.map((b) => (
                <BudgetMeter
                  key={b.budget_id}
                  budget={b}
                  actual={actualByCategory[b.category_name] || 0}
                  onSave={handleBudgetSave}
                />
              ))}
              {showAddBudget && (
                <AddBudgetForm onAdd={handleBudgetAdd} onCancel={() => setShowAddBudget(false)} />
              )}
            </div>
          )
        )}
      </section>

      <section className="dashboard-section">
        <SavingsSuggestionsPanel />
      </section>

      <section className="dashboard-section">
        <h2 className="section-title">Balance forecast</h2>
        {forecastLoading && <p>Generating forecast...</p>}
        {forecastError && <p className="status-banner status-error">{forecastError}</p>}
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
        {anomaliesLoading && <p>Analysing for unusual transactions...</p>}
        {anomaliesError && <p className="status-banner status-error">{anomaliesError}</p>}
        {!anomaliesLoading && !anomaliesError && (
          anomalies.length === 0 ? (
            <p className="empty-state">No unusual transactions flagged.</p>
          ) : (
            <ul className="anomaly-list">
              {anomalies.map((a) => (
                <li key={a.anomaly_id} className="anomaly-item">
                  <div className="anomaly-row">
                    <div className="anomaly-main">
                      <span className="anomaly-category">{a.category_name}</span>
                      <span className="anomaly-merchant">{a.merchant || "-"}</span>
                      <span className="anomaly-date">{a.txn_date}</span>
                    </div>
                    <div className="anomaly-side">
                      <span className="anomaly-amount">${Math.abs(a.amount).toFixed(2)}</span>
                    </div>
                  </div>
                  <p className="anomaly-reason">{a.reason}</p>
                </li>
              ))}
            </ul>
          )
        )}
      </section>
    </div>
  );
}

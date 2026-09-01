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
import { recommendBudgets, generateForecast, detectAnomalies } from "../lib/dashboard";

// From the dataviz skill's reference palette (references/palette.md) -
// sequential blue for magnitude, status colors reserved for severity only.
const COLORS = {
  seriesBlue: "#2a78d6",
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

function BudgetMeter({ label, actual, budget }) {
  const ratio = budget > 0 ? actual / budget : 0;
  const severity = severityFor(ratio);
  const widthPct = Math.min(ratio, 1) * 100;

  return (
    <div className="budget-card">
      <div className="budget-card-header">
        <span className="budget-card-category">{label}</span>
        <span className={`budget-card-status budget-card-status-${severity}`}>
          {SEVERITY_LABEL[severity]}
        </span>
      </div>
      <div className="meter-track">
        <div className="meter-fill" style={{ width: `${widthPct}%`, background: COLORS[severity] }} />
      </div>
      <div className="budget-card-amounts">
        <span>${actual.toFixed(2)} spent</span>
        <span className="budget-card-limit">of ${budget.toFixed(2)} budget</span>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [budgets, setBudgets] = useState([]);
  const [budgetsLoading, setBudgetsLoading] = useState(true);
  const [budgetsError, setBudgetsError] = useState("");

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
    recommendBudgets()
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
        <h2 className="section-title">Budget vs actual this month</h2>
        {budgetsLoading && <p>Loading budgets...</p>}
        {budgetsError && <p className="status-banner status-error">{budgetsError}</p>}
        {!budgetsLoading && !budgetsError && (
          budgets.length === 0 ? (
            <p className="empty-state">
              No budget recommendations yet. Sync a few months of transactions on the Transactions
              page, then check back here.
            </p>
          ) : (
            <div className="cards-grid">
              {budgets.map((b) => (
                <BudgetMeter
                  key={b.budget_id}
                  label={b.category_name}
                  actual={actualByCategory[b.category_name] || 0}
                  budget={b.recommended_amount}
                />
              ))}
            </div>
          )
        )}
      </section>

      <section className="dashboard-section">
        <h2 className="section-title">Balance forecast</h2>
        {forecastLoading && <p>Loading forecast...</p>}
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

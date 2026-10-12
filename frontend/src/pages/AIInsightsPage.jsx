import { useState } from "react";
import { analyzeStatement, askAboutStatement, downloadAIStatementReport } from "../lib/aiInsights";

function isoDate(d) {
  return d.toISOString().slice(0, 10);
}

function todayIso() {
  return isoDate(new Date());
}

function daysAgoIso(days) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return isoDate(d);
}

const PRESETS = [
  {
    label: "This month",
    getRange: () => {
      const now = new Date();
      return { startDate: isoDate(new Date(now.getFullYear(), now.getMonth(), 1)), endDate: todayIso() };
    },
  },
  {
    label: "Last month",
    getRange: () => {
      const now = new Date();
      const start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
      const end = new Date(now.getFullYear(), now.getMonth(), 0);
      return { startDate: isoDate(start), endDate: isoDate(end) };
    },
  },
  { label: "Last 3 months", getRange: () => ({ startDate: daysAgoIso(90), endDate: todayIso() }) },
  {
    label: "Year to date",
    getRange: () => {
      const now = new Date();
      return { startDate: isoDate(new Date(now.getFullYear(), 0, 1)), endDate: todayIso() };
    },
  },
];

const SUGGESTED_QUESTIONS = [
  "What increased my spending?",
  "Where can I save?",
  "Show unusual transactions",
  "Compare with last month",
];

function SeverityIcon({ severity }) {
  if (severity === "warning") return <span aria-hidden="true">{"⚠️"}</span>;
  if (severity === "positive") return <span aria-hidden="true">{"✅"}</span>;
  return <span aria-hidden="true">{"ℹ️"}</span>;
}

function EvidenceList({ evidence }) {
  if (!evidence || evidence.length === 0) return null;
  return (
    <ul className="evidence-list">
      {evidence.map((e, i) => (
        <li key={e.id ?? i} className="evidence-row">
          <span className="evidence-date">{e.date}</span>
          <span className="evidence-merchant">{e.merchant || "-"}</span>
          <span className="evidence-category">{e.category}</span>
          <span className="evidence-amount">${Math.abs(e.amount).toFixed(2)}</span>
        </li>
      ))}
    </ul>
  );
}

function InsightCard({ insight }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`insight-card insight-card-${insight.severity}`}>
      <div className="insight-card-header">
        <SeverityIcon severity={insight.severity} />
        <span className="insight-card-title">{insight.title}</span>
      </div>
      <p className="insight-card-text">{insight.text}</p>
      {insight.evidence && insight.evidence.length > 0 && (
        <>
          <button type="button" className="evidence-toggle" onClick={() => setOpen((v) => !v)}>
            {open ? "Hide evidence" : `View evidence (${insight.evidence.length})`}
          </button>
          {open && <EvidenceList evidence={insight.evidence} />}
        </>
      )}
    </div>
  );
}

export default function AIInsightsPage() {
  const [startDate, setStartDate] = useState(daysAgoIso(30));
  const [endDate, setEndDate] = useState(todayIso());
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [downloading, setDownloading] = useState(null);

  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [askAnswer, setAskAnswer] = useState(null);
  const [askError, setAskError] = useState("");

  function applyPreset(preset) {
    const range = preset.getRange();
    setStartDate(range.startDate);
    setEndDate(range.endDate);
  }

  async function handleAnalyze() {
    if (!startDate || !endDate) {
      setError("Pick a start and end date first.");
      return;
    }
    if (endDate < startDate) {
      setError("End date must be on or after the start date.");
      return;
    }
    setError("");
    setLoading(true);
    setAnalysis(null);
    setAskAnswer(null);
    try {
      const result = await analyzeStatement({ startDate, endDate });
      setAnalysis(result);
    } catch (err) {
      setError(err.message || "Failed to analyse this period");
    } finally {
      setLoading(false);
    }
  }

  async function handleAsk(presetQuestion) {
    const trimmed = (presetQuestion ?? question).trim();
    if (!trimmed || asking) return;
    setAsking(true);
    setAskError("");
    setQuestion("");
    try {
      const result = await askAboutStatement({ startDate, endDate, question: trimmed });
      setAskAnswer({ question: trimmed, ...result });
    } catch (err) {
      setAskError(err.message || "Failed to get an answer");
    } finally {
      setAsking(false);
    }
  }

  async function handleDownload(format) {
    setDownloading(format);
    try {
      await downloadAIStatementReport({ startDate, endDate, format });
    } catch (err) {
      setError(err.message || "Failed to download report");
    } finally {
      setDownloading(null);
    }
  }

  const totals = analysis?.totals;

  return (
    <div>
      <div className="page-header">
        <h1>AI Insights</h1>
      </div>
      <p className="section-subtitle">
        Pick a date range and let the AI Advisor analyse it: a financial summary, category
        breakdown, unusual spending, possible recurring charges and saving opportunities -
        every finding links back to the real transactions behind it.
      </p>

      <section className="statement-card">
        <h3 className="statement-card-title">Select a period</h3>
        <div className="statement-presets">
          {PRESETS.map((preset) => (
            <button
              key={preset.label}
              type="button"
              className="btn btn-secondary btn-small"
              onClick={() => applyPreset(preset)}
            >
              {preset.label}
            </button>
          ))}
        </div>
        <div className="statement-date-row">
          <label>
            From
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </label>
          <label>
            To
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </label>
        </div>
        {error && <p className="status-banner status-error">{error}</p>}
        <div className="statement-actions">
          <button type="button" className="btn" onClick={handleAnalyze} disabled={loading}>
            {loading ? "Analysing..." : "✨ Analyse with AI"}
          </button>
          {analysis && (
            <>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => handleDownload("csv")}
                disabled={downloading !== null}
              >
                {downloading === "csv" ? "Preparing..." : "Download AI report (CSV)"}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => handleDownload("pdf")}
                disabled={downloading !== null}
              >
                {downloading === "pdf" ? "Preparing..." : "Download AI report (PDF)"}
              </button>
            </>
          )}
        </div>
      </section>

      {loading && <p>Analysing this period with AI...</p>}

      {analysis && totals && (
        <>
          <section className="dashboard-section">
            <div className={"ai-summary-banner" + (analysis.ai_generated ? " ai-summary-live" : "")}>
              <span className="ai-summary-badge">
                {analysis.ai_generated ? "AI-generated summary" : "Computed summary"}
              </span>
              <p>{analysis.ai_summary}</p>
            </div>
          </section>

          <section className="dashboard-section">
            <h2 className="section-title">Financial summary</h2>
            <div className="insights-stat-grid">
              <div className="insights-stat-card">
                <span className="insights-stat-label">Income</span>
                <span className="insights-stat-value">${totals.income.toFixed(2)}</span>
              </div>
              <div className="insights-stat-card">
                <span className="insights-stat-label">Expenses</span>
                <span className="insights-stat-value">${totals.expenses.toFixed(2)}</span>
              </div>
              <div className="insights-stat-card">
                <span className="insights-stat-label">Net cash flow</span>
                <span className={"insights-stat-value" + (totals.savings < 0 ? " insights-stat-negative" : "")}>
                  ${totals.savings.toFixed(2)}
                </span>
              </div>
              <div className="insights-stat-card">
                <span className="insights-stat-label">Savings rate</span>
                <span className="insights-stat-value">
                  {totals.savings_rate !== null ? `${totals.savings_rate.toFixed(1)}%` : "n/a"}
                </span>
              </div>
              <div className="insights-stat-card">
                <span className="insights-stat-label">Transactions</span>
                <span className="insights-stat-value">{totals.transaction_count}</span>
              </div>
            </div>
          </section>

          <section className="dashboard-section">
            <h2 className="section-title">Category breakdown</h2>
            {totals.category_breakdown.length === 0 ? (
              <p className="empty-state">No spending recorded in this period.</p>
            ) : (
              <ul className="insights-category-list">
                {totals.category_breakdown.map((c) => {
                  const max = totals.category_breakdown[0].total || 1;
                  const widthPct = Math.min(100, (c.total / max) * 100);
                  return (
                    <li key={c.category} className="insights-category-row">
                      <span className="insights-category-name">{c.category}</span>
                      <span className="insights-category-bar-track">
                        <span className="insights-category-bar-fill" style={{ width: `${widthPct}%` }} />
                      </span>
                      <span className="insights-category-amount">${c.total.toFixed(2)}</span>
                      <span className="insights-category-count">{c.count} txns</span>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          <section className="dashboard-section">
            <h2 className="section-title">AI key insights</h2>
            {analysis.key_insights.length === 0 ? (
              <p className="empty-state">Nothing notable found for this period.</p>
            ) : (
              <div className="insight-card-list">
                {analysis.key_insights.map((insight) => (
                  <InsightCard key={insight.id} insight={insight} />
                ))}
              </div>
            )}
          </section>

          <section className="dashboard-section">
            <h2 className="section-title">Unusual spending</h2>
            {analysis.unusual_transactions.length === 0 ? (
              <p className="empty-state">No unusually large transactions flagged in this period.</p>
            ) : (
              <ul className="anomaly-list">
                {analysis.unusual_transactions.map((u, i) => (
                  <li key={u.evidence.id ?? i} className="anomaly-item">
                    <div className="anomaly-main">
                      <span className="anomaly-category">{u.evidence.category}</span>
                      <span className="anomaly-merchant">{u.evidence.merchant || "-"}</span>
                      <span className="anomaly-date">{u.evidence.date}</span>
                    </div>
                    <div className="anomaly-side">
                      <span className="anomaly-amount">${Math.abs(u.evidence.amount).toFixed(2)}</span>
                      <span className="anomaly-badge">z={u.z_score.toFixed(2)}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="dashboard-section">
            <h2 className="section-title">Possible recurring charges</h2>
            {analysis.recurring_expenses.length === 0 ? (
              <p className="empty-state">No recurring charges detected in this period.</p>
            ) : (
              <div className="cards-grid">
                {analysis.recurring_expenses.map((r) => (
                  <div key={r.merchant} className="budget-card">
                    <div className="budget-card-header">
                      <span className="budget-card-category">{r.merchant}</span>
                      <span className="budget-card-status budget-card-status-warning">{r.frequency}</span>
                    </div>
                    <div className="budget-card-amounts">
                      <span>~${r.average_amount.toFixed(2)} per charge</span>
                      <span className="budget-card-limit">seen {r.occurrences} times, last {r.last_seen}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="dashboard-section">
            <h2 className="section-title">Saving opportunities</h2>
            {analysis.saving_opportunities.length === 0 ? (
              <p className="empty-state">No categories are over budget in this period.</p>
            ) : (
              <div className="insight-card-list">
                {analysis.saving_opportunities.map((s) => (
                  <InsightCard
                    key={s.category}
                    insight={{
                      id: s.category,
                      severity: "positive",
                      title: `Over budget: ${s.category}`,
                      text: s.suggestion,
                      evidence: s.evidence,
                    }}
                  />
                ))}
              </div>
            )}
            <p className="field-hint">
              Compared against your most recent monthly budget for each category - most
              accurate when the selected period is close to a month.
            </p>
          </section>

          <section className="dashboard-section ask-ai-panel">
            <h2 className="section-title">Ask AI about this period</h2>
            <div className="ask-ai-chips">
              {SUGGESTED_QUESTIONS.map((q) => (
                <button
                  key={q}
                  type="button"
                  className="chat-quick-prompt"
                  onClick={() => handleAsk(q)}
                  disabled={asking}
                >
                  {q}
                </button>
              ))}
            </div>
            <form
              className="ask-ai-input-row"
              onSubmit={(e) => {
                e.preventDefault();
                handleAsk();
              }}
            >
              <label htmlFor="ask-ai-question" className="sr-only">
                Ask AI about this period
              </label>
              <input
                id="ask-ai-question"
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask about this period..."
                disabled={asking}
              />
              <button type="submit" className="btn" disabled={asking || !question.trim()}>
                {asking ? "Asking..." : "Ask"}
              </button>
            </form>
            {askError && <p className="status-banner status-error">{askError}</p>}
            {askAnswer && (
              <div className="ask-ai-answer">
                <p className="ask-ai-answer-question">{askAnswer.question}</p>
                <p className="ask-ai-answer-text">{askAnswer.answer}</p>
                {askAnswer.sources && askAnswer.sources.length > 0 && (
                  <p className="field-hint">Sources: {askAnswer.sources.join(", ")}</p>
                )}
                {askAnswer.evidence && askAnswer.evidence.length > 0 && <EvidenceList evidence={askAnswer.evidence} />}
              </div>
            )}
          </section>
        </>
      )}

      {!analysis && !loading && (
        <p className="empty-state">
          Pick a date range above and click "Analyse with AI" to get a full breakdown of that
          period.
        </p>
      )}
    </div>
  );
}

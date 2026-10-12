import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchSavingsSuggestions } from "../lib/savings";

const CATEGORY_ICONS = {
  dining: "🍽️",
  groceries: "🛒",
  transport: "🚗",
  transportation: "🚗",
  entertainment: "🎬",
  shopping: "🛍️",
  utilities: "💡",
  rent: "🏠",
  housing: "🏠",
  travel: "✈️",
  health: "🏥",
  healthcare: "🏥",
  education: "📚",
  subscriptions: "📺",
};

function iconFor(category) {
  return CATEGORY_ICONS[(category || "").toLowerCase()] || "💰";
}

// This panel does double duty as the Dashboard's "Savings suggestions" card
// and the Chat page's interactive "AI Insights" panel - onAskAI is only
// passed in from the Chat page, so the Ask AI button only shows up there.
export default function SavingsSuggestionsPanel({ onAskAI, title }) {
  const navigate = useNavigate();
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchSavingsSuggestions()
      .then(setSuggestions)
      .catch((err) => setError(err.message || "Failed to load savings suggestions"))
      .finally(() => setLoading(false));
  }, []);

  function viewExpenses(category) {
    navigate(`/transactions?category=${encodeURIComponent(category)}`);
  }

  function askAbout(s) {
    const question = `How can I cut back on my ${s.category} spending? I'm $${s.overspend.toFixed(2)} over budget.`;
    if (onAskAI) onAskAI(question);
  }

  return (
    <div className="savings-panel">
      <h2 className="section-title">{title || "AI Insights"}</h2>
      {loading && <p>Loading...</p>}
      {error && <p className="status-banner status-error">{error}</p>}
      {!loading && !error && (
        suggestions.length === 0 ? (
          <p className="empty-state">No categories are over budget right now - nice work.</p>
        ) : (
          <ul className="insight-card-list">
            {suggestions.map((s) => (
              <li key={s.category} className="insight-card">
                <div className="insight-card-top">
                  <span className="icon-badge insight-card-icon icon-badge-warning" aria-hidden="true">{iconFor(s.category)}</span>
                  <span className="insight-card-category">{s.category}</span>
                  <span className="insight-card-overspend">${s.overspend.toFixed(2)} over</span>
                </div>
                <p className="suggestion-text">{s.suggestion}</p>
                <div className="insight-card-actions">
                  {onAskAI && (
                    <button type="button" className="btn btn-small" onClick={() => askAbout(s)}>
                      Ask AI
                    </button>
                  )}
                  <button
                    type="button"
                    className="btn btn-secondary btn-small"
                    onClick={() => viewExpenses(s.category)}
                  >
                    View expenses
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )
      )}
    </div>
  );
}

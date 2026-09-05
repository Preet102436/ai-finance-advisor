import { useEffect, useState } from "react";
import { fetchSavingsSuggestions } from "../lib/savings";

export default function SavingsSuggestionsPanel() {
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchSavingsSuggestions()
      .then(setSuggestions)
      .catch((err) => setError(err.message || "Failed to load savings suggestions"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="savings-panel">
      <h2 className="section-title">Savings suggestions</h2>
      {loading && <p>Loading...</p>}
      {error && <p className="status-banner status-error">{error}</p>}
      {!loading && !error && (
        suggestions.length === 0 ? (
          <p className="empty-state">No categories are over budget right now - nice work.</p>
        ) : (
          <ul className="suggestion-list">
            {suggestions.map((s) => (
              <li key={s.category} className="suggestion-item">
                <div className="suggestion-header">
                  <span className="suggestion-category">{s.category}</span>
                  <span className="suggestion-overspend">${s.overspend.toFixed(2)} over</span>
                </div>
                <p className="suggestion-text">{s.suggestion}</p>
              </li>
            ))}
          </ul>
        )
      )}
    </div>
  );
}

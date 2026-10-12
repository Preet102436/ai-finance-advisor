import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchMoneyRadar } from "../lib/insights";

export default function MoneyRadarPanel({ onAskAI }) {
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState([]);
  const [dismissed, setDismissed] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchMoneyRadar()
      .then(setAlerts)
      .catch((err) => setError(err.message || "Failed to load Money Radar"))
      .finally(() => setLoading(false));
  }, []);

  const visible = alerts.filter((a) => !dismissed.includes(a.id));

  if (loading || error || visible.length === 0) return null;

  return (
    <div className="money-radar">
      <div className="money-radar-header">
        <span className="money-radar-title">Money Radar</span>
        <span className="money-radar-subtitle">Spotted automatically from your real numbers</span>
      </div>
      <div className="money-radar-cards">
        {visible.map((a) => (
          <div key={a.id} className={"money-radar-card money-radar-" + a.severity}>
            <div
              className={
                "icon-badge money-radar-card-icon icon-badge-" +
                (a.severity === "high" ? "error" : a.severity === "medium" ? "warning" : "primary")
              }
              aria-hidden="true"
            >
              {a.icon}
            </div>
            <div className="money-radar-card-body">
              <div className="money-radar-card-title">{a.title}</div>
              <p className="money-radar-card-message">{a.message}</p>
              <div className="money-radar-card-actions">
                <button
                  type="button"
                  className="btn btn-small"
                  onClick={() => onAskAI && onAskAI(a.suggested_question)}
                >
                  Ask AI
                </button>
                {a.category && (
                  <button
                    type="button"
                    className="btn btn-secondary btn-small"
                    onClick={() => navigate(`/transactions?category=${encodeURIComponent(a.category)}`)}
                  >
                    View expenses
                  </button>
                )}
              </div>
            </div>
            <button
              type="button"
              className="money-radar-dismiss"
              onClick={() => setDismissed((prev) => [...prev, a.id])}
              aria-label="Dismiss this alert"
              title="Dismiss"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

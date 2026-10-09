import { useEffect, useRef, useState } from "react";
import { fetchInsights, fetchRecentAnomalies } from "../lib/alerts";

// Alerts are recomputed client-side from /insights and /anomalies on every
// load (there's no backend alerts table to mark read/unread against), so
// "Clear all" is implemented as a locally-remembered dismissal list keyed by
// each alert's own text - any alert whose text matches something the user
// already cleared is hidden until a genuinely new one appears.
const DISMISSED_KEY = "alerts-dismissed";

function loadDismissed() {
  try {
    return new Set(JSON.parse(localStorage.getItem(DISMISSED_KEY) || "[]"));
  } catch {
    return new Set();
  }
}

function saveDismissed(keys) {
  try {
    localStorage.setItem(DISMISSED_KEY, JSON.stringify([...keys]));
  } catch {
    // Best-effort only - if storage is unavailable, alerts just won't stay
    // cleared across a reload, which isn't worth interrupting the user for.
  }
}

export default function AlertsBell() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    Promise.all([fetchInsights().catch(() => []), fetchRecentAnomalies().catch(() => [])])
      .then(([insights, anomalies]) => {
        // Only surface warning/critical insights here - "info" ones (e.g. a
        // spending decrease) belong on the Dashboard, not an alert badge.
        const insightAlerts = insights
          .filter((i) => i.severity !== "info")
          .map((i) => ({ severity: i.severity, message: i.message }));
        const anomalyAlerts = anomalies.map((a) => ({
          severity: "critical",
          message: `${a.merchant || a.category_name}: ${a.reason}`,
        }));
        const dismissed = loadDismissed();
        const all = [...insightAlerts, ...anomalyAlerts].slice(0, 15);
        setAlerts(all.filter((a) => !dismissed.has(a.message)));
      })
      .finally(() => setLoading(false));
  }, []);

  function handleClearAll() {
    const dismissed = loadDismissed();
    for (const a of alerts) dismissed.add(a.message);
    saveDismissed(dismissed);
    setAlerts([]);
  }

  useEffect(() => {
    function handleClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const count = alerts.length;

  return (
    <div className="alerts-bell-wrap" ref={containerRef}>
      <button
        className="alerts-bell-btn"
        onClick={() => setOpen((v) => !v)}
        aria-label={count > 0 ? `${count} alerts` : "No alerts"}
        aria-expanded={open}
      >
        🔔
        {count > 0 && <span className="alerts-bell-badge">{count > 9 ? "9+" : count}</span>}
      </button>

      {open && (
        <div className="alerts-dropdown" role="menu">
          <div className="alerts-dropdown-header">
            Alerts
            {!loading && alerts.length > 0 && (
              <button type="button" className="alerts-clear-all-btn" onClick={handleClearAll}>
                Clear all
              </button>
            )}
          </div>
          {loading && <p className="alerts-dropdown-empty">Loading...</p>}
          {!loading && alerts.length === 0 && (
            <p className="alerts-dropdown-empty">No alerts right now - nice work.</p>
          )}
          {!loading && alerts.length > 0 && (
            <ul className="alerts-dropdown-list">
              {alerts.map((a, i) => (
                <li key={i} className={`alerts-dropdown-item alerts-item-${a.severity}`}>
                  {a.message}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

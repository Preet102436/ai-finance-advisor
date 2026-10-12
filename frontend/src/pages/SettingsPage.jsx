import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchConsent, updateConsent, deleteMyAccount } from "../lib/settings";
import { logout } from "../lib/auth";
import {
  CURRENCIES,
  DATE_FORMATS,
  getCurrency,
  getDateFormat,
  getNotificationPrefs,
  setCurrency as persistCurrency,
  setDateFormat as persistDateFormat,
  setNotificationPrefs as persistNotificationPrefs,
} from "../lib/preferences";

export default function SettingsPage() {
  const navigate = useNavigate();

  const [consent, setConsent] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [saveMessage, setSaveMessage] = useState("");

  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  const [currency, setCurrencyState] = useState(getCurrency());
  const [dateFormat, setDateFormatState] = useState(getDateFormat());
  const [notificationPrefs, setNotificationPrefsState] = useState(getNotificationPrefs());
  const [prefsSavedMessage, setPrefsSavedMessage] = useState("");

  function flashPrefsSaved() {
    setPrefsSavedMessage("Saved.");
    setTimeout(() => setPrefsSavedMessage(""), 1500);
  }

  function handleCurrencyChange(e) {
    const value = e.target.value;
    setCurrencyState(value);
    persistCurrency(value);
    flashPrefsSaved();
  }

  function handleDateFormatChange(e) {
    const value = e.target.value;
    setDateFormatState(value);
    persistDateFormat(value);
    flashPrefsSaved();
  }

  function handleNotificationToggle(key) {
    const next = { ...notificationPrefs, [key]: !notificationPrefs[key] };
    setNotificationPrefsState(next);
    persistNotificationPrefs(next);
    flashPrefsSaved();
  }

  useEffect(() => {
    fetchConsent()
      .then((data) => setConsent(data.data_processing_consent))
      .catch((err) => setLoadError(err.message || "Failed to load settings"))
      .finally(() => setLoading(false));
  }, []);

  async function handleToggleConsent(e) {
    const next = e.target.checked;
    setConsent(next);
    setSaving(true);
    setSaveError("");
    setSaveMessage("");
    try {
      await updateConsent(next);
      setSaveMessage("Preference saved.");
    } catch (err) {
      setConsent(!next);
      setSaveError(err.message || "Failed to save preference");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    setDeleteError("");
    try {
      await deleteMyAccount();
      logout();
      navigate("/login");
    } catch (err) {
      setDeleteError(err.message || "Failed to delete account");
      setDeleting(false);
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Settings</h1>
      </div>

      <section className="dashboard-section">
        <h2 className="section-title">Display preferences</h2>
        <div className="settings-card">
          <div className="settings-preference-row">
            <label>
              Currency
              <select value={currency} onChange={handleCurrencyChange}>
                {CURRENCIES.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Date format
              <select value={dateFormat} onChange={handleDateFormatChange}>
                {DATE_FORMATS.map((d) => (
                  <option key={d.code} value={d.code}>
                    {d.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <p className="field-hint">
            Applies to amounts and dates shown on the Transactions page. Saved on this device.
          </p>
          {prefsSavedMessage && <p className="status-banner status-success">{prefsSavedMessage}</p>}
        </div>
      </section>

      <section className="dashboard-section">
        <h2 className="section-title">Notification preferences</h2>
        <div className="settings-card">
          <p className="field-hint">
            These aren't connected to any email or push notifications yet - toggling them won't
            send anything right now. They're saved here so they're ready once that's built.
          </p>
          <div className="settings-checkbox-list">
            <label className="consent-toggle">
              <input
                type="checkbox"
                checked={notificationPrefs.budgetAlerts}
                onChange={() => handleNotificationToggle("budgetAlerts")}
              />
              <span>Budget alerts - let me know when I go over budget in a category.</span>
            </label>
            <label className="consent-toggle">
              <input
                type="checkbox"
                checked={notificationPrefs.weeklySummary}
                onChange={() => handleNotificationToggle("weeklySummary")}
              />
              <span>Weekly summary - a recap of income, expenses and savings each week.</span>
            </label>
            <label className="consent-toggle">
              <input
                type="checkbox"
                checked={notificationPrefs.moneyRadarAlerts}
                onChange={() => handleNotificationToggle("moneyRadarAlerts")}
              />
              <span>Money Radar alerts - unusual spending or sharp category increases.</span>
            </label>
          </div>
        </div>
      </section>

      <section className="dashboard-section">
        <h2 className="section-title">Privacy &amp; data processing</h2>
        {loading && <p>Loading...</p>}
        {loadError && <p className="status-banner status-error">{loadError}</p>}
        {!loading && !loadError && (
          <div className="settings-card">
            <label className="consent-toggle">
              <input
                type="checkbox"
                checked={consent}
                onChange={handleToggleConsent}
                disabled={saving}
              />
              <span>
                I consent to my transaction and financial data being processed to generate
                budgets, forecasts, and personalised suggestions.
              </span>
            </label>
            {saveMessage && <p className="status-banner status-success">{saveMessage}</p>}
            {saveError && <p className="status-banner status-error">{saveError}</p>}
          </div>
        )}
      </section>

      <section className="dashboard-section">
        <h2 className="section-title">Delete your data</h2>
        <div className="settings-card settings-card-danger">
          <p>
            Permanently deletes your account and all linked data - bank account links,
            transactions, receipts, budgets, forecasts, flagged anomalies, and chat history.
            This cannot be undone.
          </p>
          {!confirmingDelete ? (
            <button className="btn btn-danger" onClick={() => setConfirmingDelete(true)}>
              Delete my data
            </button>
          ) : (
            <div className="confirm-delete">
              <p className="confirm-delete-text">Are you sure? This is permanent.</p>
              <div className="confirm-delete-actions">
                <button className="btn btn-danger" onClick={handleDelete} disabled={deleting}>
                  {deleting ? "Deleting..." : "Yes, permanently delete everything"}
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => setConfirmingDelete(false)}
                  disabled={deleting}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
          {deleteError && <p className="status-banner status-error">{deleteError}</p>}
        </div>
      </section>
    </div>
  );
}

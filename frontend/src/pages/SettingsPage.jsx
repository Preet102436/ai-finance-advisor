import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchConsent, updateConsent, deleteMyAccount } from "../lib/settings";
import { logout } from "../lib/auth";

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

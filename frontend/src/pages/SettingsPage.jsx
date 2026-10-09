import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  fetchSettings,
  updateConsent,
  updateAiEnabled,
  deleteMyAccount,
  fetchProfile,
  updateProfile,
  fetchBankAccounts,
  disconnectBankAccount,
} from "../lib/settings";
import { logout, fetchCurrentUser } from "../lib/auth";

const TABS = ["Profile", "Security", "Connected Accounts", "Privacy", "AI Preferences"];

const TAB_ICONS = {
  Profile: "👤",
  Security: "🔐",
  "Connected Accounts": "🏦",
  Privacy: "🛡️",
  "AI Preferences": "🤖",
};

function ProfileTab() {
  const [user, setUser] = useState(null);
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [income, setIncome] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");
  const [saveError, setSaveError] = useState("");

  useEffect(() => {
    Promise.all([fetchCurrentUser(), fetchProfile()])
      .then(([u, profile]) => {
        setUser(u);
        setPhone(profile.phone || "");
        setAddress(profile.address || "");
        setIncome(profile.monthly_income != null ? String(profile.monthly_income) : "");
      })
      .catch((err) => setLoadError(err.message || "Failed to load profile"))
      .finally(() => setLoading(false));
  }, []);

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setSaveError("");
    setSaveMessage("");
    try {
      await updateProfile({
        phone: phone.trim() || null,
        address: address.trim() || null,
        monthly_income: income ? parseFloat(income) : null,
      });
      setSaveMessage("Profile saved.");
    } catch (err) {
      setSaveError(err.message || "Failed to save profile");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p>Loading...</p>;
  if (loadError) return <p className="status-banner status-error">{loadError}</p>;

  return (
    <div className="settings-card">
      <div className="profile-readonly-row">
        <div>
          <span className="profile-readonly-label">Full name</span>
          <span className="profile-readonly-value">{user.full_name}</span>
        </div>
        <div>
          <span className="profile-readonly-label">Email</span>
          <span className="profile-readonly-value">{user.email}</span>
        </div>
      </div>

      <form className="settings-form" onSubmit={handleSave}>
        {saveMessage && <p className="status-banner status-success">{saveMessage}</p>}
        {saveError && <p className="status-banner status-error">{saveError}</p>}

        <label>
          Phone
          <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="e.g. 0400 000 000" />
        </label>
        <label>
          Address
          <input type="text" value={address} onChange={(e) => setAddress(e.target.value)} placeholder="e.g. 1 Example St, Sydney" />
        </label>
        <label>
          Monthly income ($)
          <input type="number" step="0.01" min="0" value={income} onChange={(e) => setIncome(e.target.value)} />
        </label>
        <button type="submit" className="btn" disabled={saving}>
          {saving ? "Saving..." : "Save profile"}
        </button>
      </form>
    </div>
  );
}

function SecurityTab() {
  return (
    <div className="settings-card">
      <ul className="security-list">
        <li>
          <strong>Password storage:</strong> your password is never stored directly - it's hashed
          with bcrypt (a one-way, salted hash) before it touches the database, so even we can't
          see your actual password.
        </li>
        <li>
          <strong>Authentication:</strong> after logging in, your session is secured with a
          signed JWT (JSON Web Token) bearer token, which expires automatically and is required
          on every request to your data.
        </li>
        <li>
          <strong>Data isolation:</strong> every API request is scoped to your own user account -
          there's no way for your transactions, budgets, or chat history to be visible to another
          user.
        </li>
        <li>
          <strong>Protected endpoints:</strong> all financial data endpoints require a valid,
          unexpired token; public endpoints are limited to registration and login only.
        </li>
        <li>
          <strong>Sandbox banking:</strong> bank linking in this app uses a mocked sandbox - no
          real bank credentials are ever collected or transmitted.
        </li>
        <li>
          <strong>API keys:</strong> the OpenAI key that powers chat and receipt scanning lives
          only in the backend's server-side configuration - it's never sent to your browser or
          exposed in any API response.
        </li>
      </ul>
    </div>
  );
}

function ConnectedAccountsTab() {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [confirmingId, setConfirmingId] = useState(null);
  const [disconnecting, setDisconnecting] = useState(false);
  const [message, setMessage] = useState(null);

  function load() {
    setLoading(true);
    fetchBankAccounts()
      .then(setAccounts)
      .catch((err) => setLoadError(err.message || "Failed to load connected accounts"))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleDisconnect(accountId) {
    setDisconnecting(true);
    setMessage(null);
    try {
      await disconnectBankAccount(accountId);
      setMessage({ type: "success", text: "Account disconnected, and its transactions removed." });
      setConfirmingId(null);
      load();
    } catch (err) {
      setMessage({ type: "error", text: err.message || "Failed to disconnect account" });
    } finally {
      setDisconnecting(false);
    }
  }

  if (loading) return <p>Loading...</p>;
  if (loadError) return <p className="status-banner status-error">{loadError}</p>;

  return (
    <div className="settings-card">
      {message && (
        <p className={message.type === "error" ? "status-banner status-error" : "status-banner status-success"}>
          {message.text}
        </p>
      )}
      {accounts.length === 0 ? (
        <p className="empty-state">
          No bank accounts linked yet. Go to Transactions to link one (demo/sandbox only).
        </p>
      ) : (
        <ul className="connected-account-list">
          {accounts.map((a) => (
            <li key={a.account_id} className="connected-account-item">
              <div>
                <span className="account-option-name">Sandbox Demo Bank</span>
                <span className="account-option-sub">
                  {a.account_type || "Account"}
                  {a.account_number_display ? ` · ${a.account_number_display}` : ""} &middot;{" "}
                  {a.currency || "AUD"} &middot; linked {new Date(a.linked_at).toLocaleDateString()}
                </span>
              </div>
              {confirmingId === a.account_id ? (
                <div className="wizard-actions">
                  <button className="btn-link" onClick={() => setConfirmingId(null)} disabled={disconnecting}>
                    Cancel
                  </button>
                  <button
                    className="btn btn-danger btn-sm"
                    onClick={() => handleDisconnect(a.account_id)}
                    disabled={disconnecting}
                  >
                    {disconnecting ? "Disconnecting..." : "Confirm disconnect"}
                  </button>
                </div>
              ) : (
                <button className="btn btn-secondary btn-sm" onClick={() => setConfirmingId(a.account_id)}>
                  Disconnect
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function PrivacyTab({ navigate }) {
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
    fetchSettings()
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

  if (loading) return <p>Loading...</p>;
  if (loadError) return <p className="status-banner status-error">{loadError}</p>;

  return (
    <>
      <div className="settings-card">
        <label className="consent-toggle">
          <input type="checkbox" checked={consent} onChange={handleToggleConsent} disabled={saving} />
          <span>
            I consent to my transaction and financial data being processed to generate budgets,
            forecasts, and personalised suggestions.
          </span>
        </label>
        {saveMessage && <p className="status-banner status-success">{saveMessage}</p>}
        {saveError && <p className="status-banner status-error">{saveError}</p>}
      </div>

      <div className="settings-card settings-card-danger">
        <h3 className="receipt-info-title">Delete your data</h3>
        <p>
          Permanently deletes your account and all linked data - bank account links, transactions,
          receipts, budgets, forecasts, flagged anomalies, and chat history. This cannot be undone.
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
              <button className="btn btn-secondary" onClick={() => setConfirmingDelete(false)} disabled={deleting}>
                Cancel
              </button>
            </div>
          </div>
        )}
        {deleteError && <p className="status-banner status-error">{deleteError}</p>}
      </div>
    </>
  );
}

function AiPreferencesTab() {
  const [aiEnabled, setAiEnabled] = useState(true);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");
  const [saveError, setSaveError] = useState("");

  useEffect(() => {
    fetchSettings()
      .then((data) => setAiEnabled(data.ai_enabled))
      .catch((err) => setLoadError(err.message || "Failed to load settings"))
      .finally(() => setLoading(false));
  }, []);

  async function handleToggle(e) {
    const next = e.target.checked;
    setAiEnabled(next);
    setSaving(true);
    setSaveError("");
    setSaveMessage("");
    try {
      await updateAiEnabled(next);
      setSaveMessage("Preference saved.");
    } catch (err) {
      setAiEnabled(!next);
      setSaveError(err.message || "Failed to save preference");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p>Loading...</p>;
  if (loadError) return <p className="status-banner status-error">{loadError}</p>;

  return (
    <div className="settings-card">
      <label className="consent-toggle">
        <input type="checkbox" checked={aiEnabled} onChange={handleToggle} disabled={saving} />
        <span>
          Use AI (large language model) for the chatbot and for reading receipt photos. When off,
          the chatbot answers with a plain-language summary of your data instead, and receipt
          scanning falls back to keyword/pattern matching - both still work, just less flexibly.
        </span>
      </label>
      {saveMessage && <p className="status-banner status-success">{saveMessage}</p>}
      {saveError && <p className="status-banner status-error">{saveError}</p>}
    </div>
  );
}

export default function SettingsPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("Profile");

  return (
    <div>
      <div className="page-header">
        <h1>Settings</h1>
      </div>

      <div className="settings-tabs">
        {TABS.map((tab) => (
          <button
            key={tab}
            className={"settings-tab" + (activeTab === tab ? " active" : "")}
            onClick={() => setActiveTab(tab)}
          >
            <span className="settings-tab-icon" aria-hidden="true">
              {TAB_ICONS[tab]}
            </span>
            {tab}
          </button>
        ))}
      </div>

      <div className="dashboard-section settings-content">
        {activeTab === "Profile" && <ProfileTab />}
        {activeTab === "Security" && <SecurityTab />}
        {activeTab === "Connected Accounts" && <ConnectedAccountsTab />}
        {activeTab === "Privacy" && <PrivacyTab navigate={navigate} />}
        {activeTab === "AI Preferences" && <AiPreferencesTab />}
      </div>
    </div>
  );
}

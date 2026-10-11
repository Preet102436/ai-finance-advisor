import { useEffect, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import { updateProfile, changePassword } from "../lib/profile";
import { fetchFinancialSummary } from "../lib/insights";
import { getInitials } from "../lib/avatar";
import ThemeToggle from "../components/ThemeToggle";

const TABS = [
  { key: "personal", label: "Personal Info" },
  { key: "financial", label: "Financial Profile" },
  { key: "preferences", label: "Preferences" },
  { key: "security", label: "Security" },
];

export default function ProfilePage() {
  const context = useOutletContext() || {};
  const { user, setUser } = context;
  const [tab, setTab] = useState("personal");

  if (!user) {
    return (
      <div>
        <div className="page-header">
          <h1>Profile</h1>
        </div>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <h1>Profile</h1>
      </div>

      <div className="profile-card">
        <span className="avatar-circle avatar-circle-large">{getInitials(user.full_name)}</span>
        <div className="profile-card-info">
          <h2 className="profile-card-name">{user.full_name}</h2>
          <p className="profile-card-email">{user.email}</p>
          <p className="profile-card-tagline">
            Member since {new Date(user.created_at).toLocaleDateString()}
          </p>
        </div>
      </div>

      <div className="profile-tabs" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={tab === t.key}
            className={"profile-tab" + (tab === t.key ? " active" : "")}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="profile-tab-panel">
        {tab === "personal" && <PersonalInfoTab user={user} onSaved={setUser} />}
        {tab === "financial" && <FinancialProfileTab />}
        {tab === "preferences" && <PreferencesTab />}
        {tab === "security" && <SecurityTab />}
      </div>
    </div>
  );
}

function PersonalInfoTab({ user, onSaved }) {
  const [fullName, setFullName] = useState(user.full_name || "");
  const [phone, setPhone] = useState(user.phone || "");
  const [dob, setDob] = useState(user.date_of_birth || "");
  const [location, setLocation] = useState(user.location || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const updated = await updateProfile({
        full_name: fullName,
        phone: phone || null,
        date_of_birth: dob || null,
        location: location || null,
      });
      if (onSaved) onSaved(updated);
      setMessage("Profile updated.");
    } catch (err) {
      setError(err.message || "Failed to update profile");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="settings-card profile-form" onSubmit={handleSubmit}>
      <label>
        Full name
        <input
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          required
          maxLength={150}
        />
      </label>
      <label>
        Email
        <input value={user.email} disabled />
        <span className="field-hint">Email can't be changed here yet.</span>
      </label>
      <label>
        Phone
        <input
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          maxLength={30}
          placeholder="e.g. 04xx xxx xxx"
        />
      </label>
      <label>
        Date of birth
        <input type="date" value={dob || ""} onChange={(e) => setDob(e.target.value)} />
      </label>
      <label>
        Location
        <input
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          maxLength={150}
          placeholder="City, Country"
        />
      </label>
      {message && <p className="status-banner status-success">{message}</p>}
      {error && <p className="status-banner status-error">{error}</p>}
      <button className="btn" type="submit" disabled={saving}>
        {saving ? "Saving..." : "Save changes"}
      </button>
    </form>
  );
}

function FinancialProfileTab() {
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchFinancialSummary()
      .then(setSummary)
      .catch((err) => setError(err.message || "Failed to load financial profile"));
  }, []);

  if (error) return <p className="status-banner status-error">{error}</p>;
  if (!summary) return <p>Loading...</p>;

  return (
    <div className="settings-card">
      <div className="profile-stat-grid">
        <div className="profile-stat">
          <span className="profile-stat-label">Financial health score</span>
          <span className="profile-stat-value">{summary.health_score ?? "-"}</span>
        </div>
        <div className="profile-stat">
          <span className="profile-stat-label">Monthly income</span>
          <span className="profile-stat-value">${summary.income.toFixed(2)}</span>
        </div>
        <div className="profile-stat">
          <span className="profile-stat-label">Monthly expenses</span>
          <span className="profile-stat-value">${summary.expenses.toFixed(2)}</span>
        </div>
        <div className="profile-stat">
          <span className="profile-stat-label">Savings rate</span>
          <span className="profile-stat-value">
            {summary.savings_rate != null ? summary.savings_rate.toFixed(1) + "%" : "-"}
          </span>
        </div>
        <div className="profile-stat">
          <span className="profile-stat-label">Top spending category</span>
          <span className="profile-stat-value">{summary.top_category || "-"}</span>
        </div>
      </div>
      <p className="field-hint">
        Pulled live from your transactions - the same numbers behind your Dashboard and the AI
        chat's answers.
      </p>
    </div>
  );
}

function PreferencesTab() {
  return (
    <div className="settings-card">
      <div className="profile-preference-row">
        <div>
          <h3 className="profile-preference-title">Appearance</h3>
          <p className="field-hint">
            Switch between light and dark mode. Applies across the whole app.
          </p>
        </div>
        <ThemeToggle className="profile-theme-toggle" />
      </div>
      <p className="field-hint">
        Manage data-processing consent and account deletion from{" "}
        <Link to="/settings">Settings</Link>.
      </p>
    </div>
  );
}

function SecurityTab() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setMessage("");
    if (newPassword !== confirmPassword) {
      setError("New passwords don't match.");
      return;
    }
    if (newPassword.length < 8) {
      setError("New password must be at least 8 characters.");
      return;
    }
    setSaving(true);
    try {
      await changePassword(currentPassword, newPassword);
      setMessage("Password updated.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setError(err.message || "Failed to update password");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="settings-card profile-form" onSubmit={handleSubmit}>
      <h3 className="profile-preference-title">Change password</h3>
      <label>
        Current password
        <input
          type="password"
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
          required
        />
      </label>
      <label>
        New password
        <input
          type="password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          required
          minLength={8}
        />
      </label>
      <label>
        Confirm new password
        <input
          type="password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          required
          minLength={8}
        />
      </label>
      {message && <p className="status-banner status-success">{message}</p>}
      {error && <p className="status-banner status-error">{error}</p>}
      <button className="btn" type="submit" disabled={saving}>
        {saving ? "Updating..." : "Update password"}
      </button>
    </form>
  );
}

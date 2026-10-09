import { useState } from "react";
import { startBankLink, completeBankLink } from "../lib/transactions";

const DEMO_BANKS = [
  { id: "sandbox", name: "Sandbox Demo Bank", enabled: true },
  { id: "cba", name: "Commonwealth Bank", enabled: false },
  { id: "anz", name: "ANZ", enabled: false },
  { id: "nab", name: "NAB", enabled: false },
];

const ACCOUNT_TYPES = ["Everyday Checking", "Savings", "Credit Card"];

// A believable-looking (but entirely made up) BSB + account number, e.g.
// "062-141 · 4821 7390" - purely cosmetic, never a real bank detail.
function randomAccountNumber() {
  const bsb = String(Math.floor(100000 + Math.random() * 900000)).replace(/(\d{3})(\d{3})/, "$1-$2");
  const number = String(Math.floor(10000000 + Math.random() * 90000000)).replace(/(\d{4})(\d{4})/, "$1 $2");
  return `${bsb} · ${number}`;
}

export default function BankLinkModal({ onClose, onConnected }) {
  const [step, setStep] = useState("select-bank"); // select-bank | consent | select-account | connecting | connected | error
  const [error, setError] = useState("");
  const [pendingAuth, setPendingAuth] = useState(null);
  const [accountType, setAccountType] = useState(ACCOUNT_TYPES[0]);
  const [accountNumber, setAccountNumber] = useState("");

  async function handleAuthorise() {
    setStep("connecting");
    setError("");
    try {
      const data = await startBankLink();
      setPendingAuth(data);
      setAccountNumber(randomAccountNumber());
      setStep("select-account");
    } catch (err) {
      setError(err.message || "Could not start the bank link. Please try again.");
      setStep("error");
    }
  }

  async function handleConnectAccount() {
    setStep("connecting");
    setError("");
    try {
      await completeBankLink(pendingAuth.auth_code, pendingAuth.state, {
        accountType,
        accountNumberDisplay: accountNumber,
      });
      setStep("connected");
    } catch (err) {
      setError(err.message || "Could not connect this account. Please try again.");
      setStep("error");
    }
  }

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="Link a bank account">
      <div className="modal-card">
        <div className="modal-header">
          <h2>Link a bank account</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            &times;
          </button>
        </div>

        <p className="sandbox-notice">
          This is a demo/sandbox banking connection &mdash; no real bank account is contacted,
          and no real financial credentials are ever collected.
        </p>

        {step === "select-bank" && (
          <div className="bank-wizard-step">
            <p className="wizard-step-label">Step 1 of 3 &mdash; Select your bank</p>
            <ul className="bank-list">
              {DEMO_BANKS.map((bank) => (
                <li key={bank.id}>
                  <button
                    className="bank-list-item"
                    disabled={!bank.enabled}
                    onClick={() => setStep("consent")}
                  >
                    <span>{bank.name}</span>
                    {!bank.enabled && <span className="bank-list-badge">Coming soon</span>}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {step === "consent" && (
          <div className="bank-wizard-step">
            <p className="wizard-step-label">Step 2 of 3 &mdash; Consent &amp; authorisation</p>
            <div className="consent-box">
              <p>
                By continuing, you authorise this app to access simulated transaction data
                from <strong>Sandbox Demo Bank</strong> for demonstration purposes. No real
                banking data is shared.
              </p>
              <ul className="consent-list">
                <li>Read access to mock account transactions</li>
                <li>No access to move money or make payments</li>
                <li>You can disconnect at any time from Settings</li>
              </ul>
            </div>
            <div className="wizard-actions">
              <button className="btn btn-secondary" onClick={() => setStep("select-bank")}>
                Back
              </button>
              <button className="btn" onClick={handleAuthorise}>
                Authorise
              </button>
            </div>
          </div>
        )}

        {step === "connecting" && (
          <div className="bank-wizard-step wizard-center">
            <div className="spinner" aria-hidden="true" />
            <p>Connecting&hellip;</p>
          </div>
        )}

        {step === "select-account" && pendingAuth && (
          <div className="bank-wizard-step">
            <p className="wizard-step-label">Step 3 of 3 &mdash; Select an account</p>
            <div className="account-option account-option-static">
              <span className="account-option-icon" aria-hidden="true">
                🏦
              </span>
              <span className="account-option-details">
                <label className="account-field">
                  Account type
                  <select value={accountType} onChange={(e) => setAccountType(e.target.value)}>
                    {ACCOUNT_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="account-field">
                  Account number (sandbox)
                  <input
                    type="text"
                    value={accountNumber}
                    onChange={(e) => setAccountNumber(e.target.value)}
                  />
                </label>
                <span className="account-option-sub">Sandbox Demo Bank &middot; AUD</span>
              </span>
            </div>
            <div className="wizard-actions">
              <button className="btn btn-secondary" onClick={() => setStep("consent")}>
                Back
              </button>
              <button className="btn" onClick={handleConnectAccount}>
                Connect this account
              </button>
            </div>
          </div>
        )}

        {step === "connected" && (
          <div className="bank-wizard-step wizard-center">
            <div className="wizard-success-icon" aria-hidden="true">
              ✓
            </div>
            <p>
              <strong>Account connected.</strong>
            </p>
            <p className="empty-state">You can now sync transactions from the Transactions page.</p>
            <button
              className="btn"
              onClick={() => {
                onConnected();
                onClose();
              }}
            >
              Done
            </button>
          </div>
        )}

        {step === "error" && (
          <div className="bank-wizard-step">
            <p className="status-banner status-error">{error}</p>
            <div className="wizard-actions">
              <button className="btn btn-secondary" onClick={onClose}>
                Cancel
              </button>
              <button className="btn" onClick={() => setStep("select-bank")}>
                Try again
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchBankAccounts } from "../lib/settings";

export default function OnboardingChecklist({ hasTransactions, hasBudgets }) {
  const [hasAccount, setHasAccount] = useState(false);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    fetchBankAccounts()
      .then((accounts) => setHasAccount(accounts.length > 0))
      .catch(() => {})
      .finally(() => setChecked(true));
  }, []);

  const steps = [
    {
      done: hasAccount,
      title: "Connect your bank",
      text: "Link a demo/sandbox bank account.",
      to: "/transactions",
      cta: "Link bank account",
    },
    {
      done: hasTransactions,
      title: "Sync transactions",
      text: "Pull in sample transactions, or scan a receipt / add an expense manually.",
      to: "/transactions",
      cta: "Go to Transactions",
    },
    {
      done: hasBudgets,
      title: "Set a budget or goal",
      text: "Let AI recommend budgets from your spending, or set one yourself.",
      to: "/dashboard",
      cta: "View budgets",
    },
    {
      done: false,
      title: "View AI insights",
      text: "See spending trends, forecasts, and personalised savings tips.",
      to: "/chat",
      cta: "Ask the chatbot",
    },
  ];

  if (!checked) return null;

  return (
    <section className="dashboard-section">
      <div className="onboarding-card">
        <h2 className="section-title">Welcome - let's get you set up</h2>
        <ol className="onboarding-steps">
          {steps.map((step, i) => (
            <li key={step.title} className={"onboarding-step" + (step.done ? " onboarding-step-done" : "")}>
              <span className="onboarding-step-number">{step.done ? "✓" : i + 1}</span>
              <div className="onboarding-step-body">
                <span className="onboarding-step-title">{step.title}</span>
                <span className="onboarding-step-text">{step.text}</span>
              </div>
              {!step.done && (
                <Link to={step.to} className="btn btn-secondary btn-sm">
                  {step.cta}
                </Link>
              )}
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

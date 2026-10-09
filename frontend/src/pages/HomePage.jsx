import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { isAuthenticated } from "../lib/auth";

// Scroll-reveal: fades/slides in any ".reveal" element inside the page once
// it enters the viewport, so the feature cards and steps animate in as the
// user scrolls instead of all appearing at once with the rest of the page.
function useScrollReveal(containerRef) {
  useEffect(() => {
    const els = containerRef.current ? containerRef.current.querySelectorAll(".reveal") : [];
    if (!els.length || typeof IntersectionObserver === "undefined") {
      els.forEach((el) => el.classList.add("is-visible"));
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
    );
    els.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [containerRef]);
}

const FEATURES = [
  {
    icon: "🏦",
    title: "Connect your bank",
    text: "Link a bank account (demo/sandbox) and sync transactions automatically.",
  },
  {
    icon: "🧾",
    title: "Scan receipts",
    text: "Snap a receipt and AI reads the merchant, total and category for you to confirm.",
  },
  {
    icon: "💰",
    title: "AI budgets",
    text: "Get a personalised monthly budget per category, generated from your real spending.",
  },
  {
    icon: "📈",
    title: "Forecasts & anomalies",
    text: "See where your balance is headed, and get flagged the moment something looks unusual.",
  },
  {
    icon: "🤖",
    title: "Ask the AI chatbot",
    text: "“How much did I spend on dining?” — get answers grounded in your real transactions.",
  },
  {
    icon: "💡",
    title: "Savings suggestions",
    text: "Actionable tips, like “Reduce dining by $40/month → save $480/year.”",
  },
];

const HOW_IT_WORKS = [
  { title: "Connect & sync", text: "Link a sandbox bank account and sync your transactions in seconds." },
  { title: "Set a budget & goal", text: "Get an AI-recommended budget per category, or set your own." },
  { title: "See insights, instantly", text: "Dashboard, forecasts, anomaly alerts and a chatbot — all grounded in your data." },
];

export default function HomePage() {
  const loggedIn = isAuthenticated();
  const pageRef = useRef(null);
  useScrollReveal(pageRef);

  return (
    <div className="home-page" ref={pageRef}>
      <header className="home-nav">
        <div className="home-brand">AI Finance Advisor</div>
        <nav className="home-nav-actions">
          {loggedIn ? (
            <Link to="/dashboard" className="btn">
              Go to Dashboard
            </Link>
          ) : (
            <>
              <Link to="/login" className="btn btn-secondary">
                Log in
              </Link>
              <Link to="/register" className="btn">
                Get started
              </Link>
            </>
          )}
        </nav>
      </header>

      <section className="home-hero">
        <span className="home-badge">Demo / sandbox banking data — no real bank connection</span>
        <h1>Understand your money, without the spreadsheet.</h1>
        <p>
          AI-powered budgeting, receipt scanning, spending forecasts and a finance chatbot
          — all grounded in your real transaction history.
        </p>
        <div className="home-hero-actions">
          <Link to={loggedIn ? "/dashboard" : "/register"} className="btn btn-lg">
            {loggedIn ? "Go to Dashboard" : "Create a free account"}
          </Link>
          <Link to={loggedIn ? "/transactions" : "/login"} className="btn btn-secondary btn-lg">
            {loggedIn ? "View transactions" : "I already have an account"}
          </Link>
        </div>
      </section>

      <section className="home-features">
        {FEATURES.map((f, i) => (
          <div className="reveal" style={{ transitionDelay: `${(i % 3) * 80}ms` }} key={f.title}>
            <div className="home-feature-card">
              <div className="home-feature-icon" aria-hidden="true">
                {f.icon}
              </div>
              <h3>{f.title}</h3>
              <p>{f.text}</p>
            </div>
          </div>
        ))}
      </section>

      <section className="home-steps">
        <h2 className="home-steps-title reveal">How it works</h2>
        <div className="home-steps-grid">
          {HOW_IT_WORKS.map((step, i) => (
            <div className="reveal" style={{ transitionDelay: `${i * 100}ms` }} key={step.title}>
              <div className="home-step">
                <div className="home-step-number">{i + 1}</div>
                <h3>{step.title}</h3>
                <p>{step.text}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <footer className="home-footer">
        <p>COIT20273 capstone project &mdash; AI-Powered Personal Finance Advisor</p>
      </footer>
    </div>
  );
}

import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { fetchCurrentUser, logout } from "../lib/auth";
import LogoMark from "./LogoMark";
import ThemeToggle from "./ThemeToggle";
import TopBar from "./TopBar";

function DashboardIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="3" y="12" width="4" height="9" rx="1" stroke="currentColor" strokeWidth="1.6" />
      <rect x="10" y="7" width="4" height="14" rx="1" stroke="currentColor" strokeWidth="1.6" />
      <rect x="17" y="3" width="4" height="18" rx="1" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
}

function TransactionsIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M6 3H18V21L15 19L12 21L9 19L6 21V3Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M9 8H15M9 12H15" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M4 5H20V15H12L7 19V15H4V5Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function AIInsightsIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 3L13.6 8.2L19 9.8L13.6 11.4L12 16.6L10.4 11.4L5 9.8L10.4 8.2L12 3Z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <path d="M18.5 15.5L19.2 17.7L21.4 18.4L19.2 19.1L18.5 21.3L17.8 19.1L15.6 18.4L17.8 17.7L18.5 15.5Z" stroke="currentColor" strokeWidth="1.1" strokeLinejoin="round" />
    </svg>
  );
}

function SettingsIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="M12 3V5.2M12 18.8V21M21 12H18.8M5.2 12H3M18.0 6.0L16.5 7.5M7.5 16.5L6.0 18.0M18.0 18.0L16.5 16.5M7.5 7.5L6.0 6.0"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

function ProfileIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="8" r="3.4" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="M5 20C5.8 16.5 8.5 14.5 12 14.5C15.5 14.5 18.2 16.5 19 20"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", Icon: DashboardIcon },
  { to: "/transactions", label: "Transactions", Icon: TransactionsIcon },
  { to: "/chat", label: "AI Advisor", Icon: ChatIcon },
  { to: "/ai-insights", label: "AI Insights", Icon: AIInsightsIcon },
  { to: "/profile", label: "Profile", Icon: ProfileIcon },
  { to: "/settings", label: "Settings", Icon: SettingsIcon },
];

export default function Layout() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  // On a phone/narrow screen the sidebar becomes a slide-in drawer instead
  // of taking a fixed 220px out of the content width (see the max-width:
  // 860px rules in index.css) - this just tracks whether it's open.
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    fetchCurrentUser()
      .then(setUser)
      .catch(() => {
        // TopBar/ProfilePage just show a generic placeholder until this
        // resolves - no need to surface an error for a background fetch.
      });
  }, []);

  function handleLogout() {
    logout();
    navigate("/login");
  }

  function closeMobileNav() {
    setMobileNavOpen(false);
  }

  return (
    <div className="app-shell">
      {mobileNavOpen && <div className="mobile-nav-backdrop" onClick={closeMobileNav} />}
      <aside className={"sidebar" + (mobileNavOpen ? " sidebar-mobile-open" : "")}>
        <div className="sidebar-brand">
          <LogoMark />
          <span>AI Finance Advisor</span>
        </div>
        <p className="sidebar-tagline">Smarter money. Brighter tomorrow.</p>
        <nav>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}
              onClick={closeMobileNav}
            >
              <item.Icon />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <ThemeToggle className="sidebar-theme-toggle" />
        <button className="logout-button" onClick={handleLogout}>
          Log out
        </button>
      </aside>
      <div className="main-area">
        <TopBar user={user} onMenuToggle={() => setMobileNavOpen((v) => !v)} />
        <main className="content">
          <Outlet context={{ user, setUser }} />
        </main>
      </div>
    </div>
  );
}

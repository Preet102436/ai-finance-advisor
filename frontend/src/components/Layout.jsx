import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { logout } from "../lib/auth";
import AlertsBell from "./AlertsBell";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: "📊" },
  { to: "/transactions", label: "Transactions", icon: "💳" },
  { to: "/chat", label: "Chat", icon: "💬" },
  { to: "/settings", label: "Settings", icon: "⚙️" },
];

export default function Layout() {
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span aria-hidden="true">💰</span> AI Finance Advisor
        </div>
        <nav>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}
            >
              <span className="sidebar-link-icon" aria-hidden="true">
                {item.icon}
              </span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <button className="logout-button" onClick={handleLogout}>
          Log out
        </button>
      </aside>
      <main className="content">
        <div className="content-topbar">
          <AlertsBell />
        </div>
        <Outlet />
      </main>
    </div>
  );
}

import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { logout } from "../lib/auth";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/transactions", label: "Transactions" },
  { to: "/chat", label: "Chat" },
  { to: "/settings", label: "Settings" },
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
        <div className="sidebar-brand">AI Finance Advisor</div>
        <nav>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <button className="logout-button" onClick={handleLogout}>
          Log out
        </button>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}

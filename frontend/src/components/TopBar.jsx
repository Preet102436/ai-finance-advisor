import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { logout } from "../lib/auth";
import { getInitials } from "../lib/avatar";

function MenuIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M4 7H20M4 12H20M4 17H20" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

// Sits above the page content next to the sidebar. Shows the signed-in
// user's initials and name, with a small dropdown to Profile/Settings/Log
// out - no notification bell, since there's no notification system behind
// one yet. On narrow screens the sidebar becomes a slide-in drawer, and
// onMenuToggle (passed from Layout) opens/closes it via the hamburger
// button that only shows up at that width (see .mobile-menu-button).
export default function TopBar({ user, onMenuToggle }) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleLogout() {
    logout();
    navigate("/login");
  }

  const initials = getInitials(user?.full_name);

  return (
    <header className="top-bar">
      <button
        type="button"
        className="mobile-menu-button"
        onClick={onMenuToggle}
        aria-label="Open navigation menu"
      >
        <MenuIcon />
      </button>
      <div className="top-bar-spacer" />
      <div className="top-bar-account" ref={menuRef}>
        <button
          type="button"
          className="top-bar-avatar-button"
          onClick={() => setOpen((v) => !v)}
          aria-haspopup="true"
          aria-expanded={open}
        >
          <span className="avatar-circle avatar-circle-small">{initials}</span>
          <span className="top-bar-name">{user ? user.full_name : "Account"}</span>
        </button>
        {open && (
          <div className="top-bar-menu" role="menu">
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                navigate("/profile");
              }}
            >
              Profile
            </button>
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                navigate("/settings");
              }}
            >
              Settings
            </button>
            <button
              type="button"
              role="menuitem"
              className="top-bar-menu-danger"
              onClick={handleLogout}
            >
              Log out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

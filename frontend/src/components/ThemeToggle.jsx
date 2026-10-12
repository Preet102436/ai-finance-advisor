import { useState } from "react";
import { applyTheme, getPreferredTheme } from "../lib/theme";

// Reads the theme the inline bootstrap script in index.html already applied
// to <html data-theme="..."> before React mounted, so there's no mismatch
// between what's on screen and what this toggle thinks the state is.
function currentTheme() {
  if (typeof document === "undefined") return "light";
  return document.documentElement.getAttribute("data-theme") || getPreferredTheme();
}

export default function ThemeToggle({ className }) {
  const [theme, setTheme] = useState(currentTheme());

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    applyTheme(next);
    setTheme(next);
  }

  return (
    <button
      type="button"
      className={"theme-toggle" + (className ? " " + className : "")}
      onClick={toggle}
      aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
    >
      <span className="theme-toggle-icon" aria-hidden="true">
        {theme === "dark" ? "☀️" : "🌙"}
      </span>
      <span>{theme === "dark" ? "Light mode" : "Dark mode"}</span>
    </button>
  );
}

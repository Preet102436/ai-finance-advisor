// Client-side display + notification preferences, stored the same way
// lib/theme.js stores the dark/light mode choice - per-device, no backend
// round trip needed. Notification prefs are saved here but nothing reads
// them yet (there is no email/push system in this app); they exist so a
// real notification feature has somewhere to read a setting from later,
// without pretending anything gets sent today.

const CURRENCY_KEY = "pref_currency";
const DATE_FORMAT_KEY = "pref_date_format";
const NOTIFICATIONS_KEY = "pref_notifications";

export const CURRENCIES = [
  { code: "AUD", label: "Australian Dollar (AUD)", symbol: "$" },
  { code: "USD", label: "US Dollar (USD)", symbol: "$" },
  { code: "EUR", label: "Euro (EUR)", symbol: "€" },
  { code: "GBP", label: "British Pound (GBP)", symbol: "£" },
];

export const DATE_FORMATS = [
  { code: "YYYY-MM-DD", label: "2026-01-21 (YYYY-MM-DD)" },
  { code: "DD/MM/YYYY", label: "21/01/2026 (DD/MM/YYYY)" },
  { code: "MM/DD/YYYY", label: "01/21/2026 (MM/DD/YYYY)" },
];

export const DEFAULT_NOTIFICATION_PREFS = {
  budgetAlerts: false,
  weeklySummary: false,
  moneyRadarAlerts: false,
};

export function getCurrency() {
  try {
    return localStorage.getItem(CURRENCY_KEY) || "AUD";
  } catch {
    return "AUD";
  }
}

export function setCurrency(code) {
  try {
    localStorage.setItem(CURRENCY_KEY, code);
  } catch {
    // Private browsing / storage disabled - just won't persist across reloads.
  }
}

export function getDateFormat() {
  try {
    return localStorage.getItem(DATE_FORMAT_KEY) || "YYYY-MM-DD";
  } catch {
    return "YYYY-MM-DD";
  }
}

export function setDateFormat(code) {
  try {
    localStorage.setItem(DATE_FORMAT_KEY, code);
  } catch {
    // Same as above - non-fatal.
  }
}

export function getNotificationPrefs() {
  try {
    const raw = localStorage.getItem(NOTIFICATIONS_KEY);
    if (!raw) return { ...DEFAULT_NOTIFICATION_PREFS };
    return { ...DEFAULT_NOTIFICATION_PREFS, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULT_NOTIFICATION_PREFS };
  }
}

export function setNotificationPrefs(prefs) {
  try {
    localStorage.setItem(NOTIFICATIONS_KEY, JSON.stringify(prefs));
  } catch {
    // Non-fatal - see getCurrency().
  }
}

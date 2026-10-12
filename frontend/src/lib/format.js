import { CURRENCIES, getCurrency, getDateFormat } from "./preferences";

export function formatCurrency(amount) {
  const code = getCurrency();
  const currency = CURRENCIES.find((c) => c.code === code) || CURRENCIES[0];
  const sign = amount < 0 ? "-" : "";
  return `${sign}${currency.symbol}${Math.abs(amount).toFixed(2)}`;
}

// isoDateStr is a plain "YYYY-MM-DD" (or longer ISO string - only the date
// part is used) as the backend always sends dates.
export function formatDate(isoDateStr) {
  if (!isoDateStr) return "";
  const [year, month, day] = isoDateStr.slice(0, 10).split("-");
  if (!year || !month || !day) return isoDateStr;
  const format = getDateFormat();
  if (format === "DD/MM/YYYY") return `${day}/${month}/${year}`;
  if (format === "MM/DD/YYYY") return `${month}/${day}/${year}`;
  return `${year}-${month}-${day}`;
}

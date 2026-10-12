import { API_BASE_URL, getToken } from "./apiClient";

// Shared by statement.js and profile.js's data export - both need a real
// file download with an auth header attached, which a plain <a href> can't
// do and apiClient.get() doesn't support (it always parses JSON).
export async function downloadFile(path, filename) {
  const token = getToken();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const data = await response.json();
      if (data && typeof data.detail === "string") message = data.detail;
    } catch {
      // Body wasn't JSON (e.g. a plain-text error) - keep the generic message.
    }
    throw new Error(message);
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

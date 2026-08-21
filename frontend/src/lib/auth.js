import { apiClient, setToken, clearToken, isAuthenticated, getToken } from "./apiClient";

export { isAuthenticated, getToken };

export async function register({ fullName, email, password }) {
  return apiClient.post("/auth/register", {
    full_name: fullName,
    email,
    password,
  });
}

export async function login({ email, password }) {
  const data = await apiClient.post("/auth/login", { email, password });
  setToken(data.access_token);
  return data;
}

export function logout() {
  clearToken();
}

export async function fetchCurrentUser() {
  return apiClient.get("/users/me", { auth: true });
}

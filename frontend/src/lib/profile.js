import { apiClient } from "./apiClient";

export async function fetchProfile() {
  return apiClient.get("/users/me", { auth: true });
}

export async function updateProfile(fields) {
  return apiClient.patch("/users/me", fields, { auth: true });
}

export async function changePassword(currentPassword, newPassword) {
  return apiClient.put(
    "/users/me/password",
    { current_password: currentPassword, new_password: newPassword },
    { auth: true }
  );
}

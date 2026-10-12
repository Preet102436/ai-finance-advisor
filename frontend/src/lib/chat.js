import { apiClient } from "./apiClient";

export async function sendChatMessage(question) {
  return apiClient.post("/chat/messages", { question }, { auth: true });
}

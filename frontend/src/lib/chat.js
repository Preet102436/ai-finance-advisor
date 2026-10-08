import { apiClient } from "./apiClient";

export async function sendChatMessage(question) {
  return apiClient.post("/chat/messages", { question }, { auth: true });
}

export async function rateChatMessage(messageId, rating) {
  return apiClient.put(`/chat/messages/${messageId}/rating`, { rating }, { auth: true });
}

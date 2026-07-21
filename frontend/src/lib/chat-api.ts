import { request } from "./api";

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ChatReply {
  reply: string;
  conversation_id: number;
}

export function getChatHistory(): Promise<ChatMessage[]> {
  return request<ChatMessage[]>("/api/ai/history");
}

export function sendChatMessage(message: string, today: string): Promise<ChatReply> {
  return request<ChatReply>("/api/ai/chat", {
    method: "POST",
    body: JSON.stringify({ message, today }),
  });
}

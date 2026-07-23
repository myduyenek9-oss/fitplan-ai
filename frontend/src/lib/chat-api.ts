import type { DailySummary, ExerciseRecord, FoodRecord } from "./fitplan-api";
import { request } from "./api";

export interface PlanAdjustment {
  action: "postpone_training" | "replace_meal";
  status: "applied" | "not_applicable" | "failed";
  plan_id: number | null;
  source_date: string;
  target_date: string | null;
  meal_type?: "breakfast" | "lunch" | "snack" | "dinner" | null;
  previous_meal_name?: string | null;
  updated_meal_name?: string | null;
  message: string;
}

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  recorded_food?: FoodRecord | null;
  recorded_exercise?: ExerciseRecord | null;
  plan_adjustment?: PlanAdjustment | null;
}

export interface ChatReply {
  reply: string;
  conversation_id: number;
  user_message_id: number;
  user_created_at: string;
  assistant_created_at: string;
  recorded_food: FoodRecord | null;
  recorded_exercise: ExerciseRecord | null;
  daily_summary: DailySummary | null;
  plan_adjustment: PlanAdjustment | null;
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

export interface ChatHistoryDeleteResult {
  deleted_count: number;
}

export function deleteChatMessages(messageIds: number[]): Promise<ChatHistoryDeleteResult> {
  return request<ChatHistoryDeleteResult>("/api/ai/history/delete", {
    method: "POST",
    body: JSON.stringify({ message_ids: messageIds }),
  });
}

export function clearChatHistory(): Promise<ChatHistoryDeleteResult> {
  return request<ChatHistoryDeleteResult>("/api/ai/history", { method: "DELETE" });
}

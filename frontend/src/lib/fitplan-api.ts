import { request } from "./api";

export type FoodStatus = "active" | "deleted" | "undone";

export interface FoodRecord {
  id: number;
  user_id: number;
  original_text: string;
  parsed_content: Record<string, unknown>;
  meal_type: string | null;
  calories: number;
  protein_g: number;
  carb_g: number;
  fat_g: number;
  status: FoodStatus;
  logged_at: string;
  created_at: string;
  updated_at: string;
}

export interface ExerciseRecord {
  id: number;
  user_id: number;
  exercise_type: string;
  description: string | null;
  duration_minutes: number;
  calories_burned: number;
  logged_at: string;
  created_at: string;
  updated_at: string;
}

export interface DailySummary {
  date: string;
  goal: {
    daily_calories: number;
    protein_g: number;
    carb_g: number;
    fat_g: number;
  } | null;
  food_totals: {
    calories: number;
    protein_g: number;
    carb_g: number;
    fat_g: number;
  };
  exercise_totals: {
    calories_burned: number;
    duration_minutes: number;
  };
  remaining_calories: number | null;
  macro_completion_percentages: {
    protein_g: number | null;
    carb_g: number | null;
    fat_g: number | null;
  };
  food_status_counts: Record<FoodStatus, number>;
  food_records: FoodRecord[];
  exercise_records: ExerciseRecord[];
}

export interface NaturalLanguageFoodResult {
  record: FoodRecord;
  daily_summary: DailySummary;
  adjustment_suggestion: string;
  conversation_id: number;
}

export function getDailySummary(date: string): Promise<DailySummary> {
  return request<DailySummary>(`/api/records/daily?date=${encodeURIComponent(date)}`);
}

export function logFoodFromText(text: string, today: string): Promise<NaturalLanguageFoodResult> {
  return request<NaturalLanguageFoodResult>("/api/records/food/natural-language", {
    method: "POST",
    body: JSON.stringify({ text, today }),
  });
}

export function undoFoodRecord(recordId: number): Promise<FoodRecord> {
  return request<FoodRecord>(`/api/records/food/${recordId}/undo`, {
    method: "POST",
  });
}

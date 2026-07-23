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
  calories_min?: number | null;
  calories_max?: number | null;
  status: FoodStatus;
  logged_at: string;
  created_at: string;
  updated_at: string;
}

export interface ExerciseRecord {
  id: number;
  user_id: number;
  original_text?: string | null;
  exercise_type: string;
  description: string | null;
  duration_minutes: number;
  calories_burned: number;
  calories_burned_min?: number | null;
  calories_burned_max?: number | null;
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
  calorie_calculation?: { formula: string; exercise_included_fully: boolean; explanation: string };
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
  record: FoodRecord | ExerciseRecord;
  recorded_food?: FoodRecord | null;
  recorded_exercise: ExerciseRecord | null;
  daily_summary: DailySummary;
  adjustment_suggestion: string;
  conversation_id: number;
}

export interface NaturalLanguageExerciseResult {
  record: ExerciseRecord;
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

export function logExerciseFromText(text: string, today: string): Promise<NaturalLanguageExerciseResult> {
  return request<NaturalLanguageExerciseResult>("/api/records/exercise/natural-language", {
    method: "POST",
    body: JSON.stringify({ text, today }),
  });
}

export function undoFoodRecord(recordId: number): Promise<FoodRecord> {
  return request<FoodRecord>(`/api/records/food/${recordId}/undo`, {
    method: "POST",
  });
}

export function undoExerciseRecord(recordId: number): Promise<void> {
  return request<void>(`/api/records/exercise/${recordId}/undo`, {
    method: "POST",
  });
}


export function updateFoodRecord(recordId: number, payload: Partial<Pick<FoodRecord, "original_text" | "calories" | "protein_g" | "carb_g" | "fat_g" | "meal_type" | "logged_at">>): Promise<FoodRecord> {
  return request<FoodRecord>(`/api/records/food/${recordId}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function updateExerciseRecord(recordId: number, payload: Partial<Pick<ExerciseRecord, "original_text" | "exercise_type" | "description" | "duration_minutes" | "calories_burned" | "logged_at">>): Promise<ExerciseRecord> {
  return request<ExerciseRecord>(`/api/records/exercise/${recordId}`, { method: "PATCH", body: JSON.stringify(payload) });
}

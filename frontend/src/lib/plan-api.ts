import { request } from "./api";

export type MealType = "breakfast" | "lunch" | "dinner" | "snack" | null;

export interface PlanFood {
  name: string;
  amount: string;
  notes: string | null;
}

export interface PlanMeal {
  name: string;
  meal_type: MealType;
  calories: number;
  protein_g: number;
  carb_g: number;
  fat_g: number;
  foods: PlanFood[];
}

export interface PlanWorkoutExercise {
  name: string;
  sets: number;
  reps: string;
  rest_seconds: number;
  notes: string | null;
}

export interface PlanWorkout {
  kind: "workout" | "rest";
  title: string;
  instructions: string;
  duration_minutes: number | null;
  split: string | null;
  focus: string | null;
  warmup: string | null;
  exercises: PlanWorkoutExercise[];
  cooldown: string | null;
}

export interface PlanDay {
  date: string;
  calorie_target: number;
  meals: PlanMeal[];
  training_instruction: PlanWorkout;
}

export interface FitnessPlan {
  id: number;
  user_id: number;
  title: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
  days: PlanDay[];
  created_at: string;
  updated_at: string;
}

export function getCurrentPlan(): Promise<FitnessPlan> {
  return request<FitnessPlan>("/api/plans/current");
}

export function generatePlan(startDate: string, title = "我的 7 天饮食训练计划"): Promise<FitnessPlan> {
  return request<FitnessPlan>("/api/plans/generate", {
    method: "POST",
    body: JSON.stringify({ start_date: startDate, title }),
  });
}

export function postponePlanDay(planId: number, day: string): Promise<FitnessPlan> {
  return request<FitnessPlan>(`/api/plans/${planId}/days/${day}/postpone`, { method: "POST" });
}

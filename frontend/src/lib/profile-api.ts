import { request } from "./api";

export type ProfileSex = "male" | "female" | "other" | "unspecified";
export type CalorieSex = "male" | "female";
export type GoalType = "fat_loss" | "maintenance" | "muscle_gain";
export type ActivityLevel = "sedentary" | "light" | "moderate" | "active" | "very_active";

export type Profile = {
  id: number;
  user_id: number;
  display_name: string | null;
  sex: ProfileSex | null;
  birth_date: string | null;
  height_cm: number | null;
  timezone: string | null;
  created_at: string;
  updated_at: string;
};

export type ProfileInput = {
  display_name?: string | null;
  sex?: ProfileSex | null;
  birth_date?: string | null;
  height_cm?: number | null;
  timezone?: string | null;
};

export type GoalInput = {
  goal_type: GoalType;
  daily_calories: number;
  protein_g: number;
  carb_g: number;
  fat_g: number;
  activity_level: ActivityLevel;
  target_weight_kg?: number | null;
  target_date?: string | null;
};

export type Goal = GoalInput & {
  id: number;
  user_id: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type BodyMetricInput = {
  weight_kg?: number | null;
  body_fat_percent?: number | null;
  waist_cm?: number | null;
  chest_cm?: number | null;
  hip_cm?: number | null;
  notes?: string | null;
  logged_at: string;
};

export type CaloriePreviewInput = {
  age: number;
  sex: CalorieSex;
  weight_kg: number;
  height_cm: number;
  activity_level: ActivityLevel;
  goal: GoalType;
};

export type CalorieTargets = {
  bmr: number;
  tdee: number;
  daily_calories: number;
  protein_g: number;
  carb_g: number;
  fat_g: number;
};

export function getProfile(): Promise<Profile> {
  return request<Profile>("/api/profile");
}

export function upsertProfile(payload: ProfileInput): Promise<Profile> {
  return request<Profile>("/api/profile", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function upsertGoal(payload: GoalInput): Promise<Goal> {
  return request<Goal>("/api/profile/goal", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function createBodyMetric(payload: BodyMetricInput): Promise<BodyMetricInput & { id: number }> {
  return request<BodyMetricInput & { id: number }>("/api/body-metrics", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function previewCalorieTargets(payload: CaloriePreviewInput): Promise<CalorieTargets> {
  return request<CalorieTargets>("/api/calorie/preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

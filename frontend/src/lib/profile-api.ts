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

export type BodyMetric = BodyMetricInput & {
  id: number;
  user_id: number;
  created_at: string;
  updated_at: string;
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

export function getActiveGoal(): Promise<Goal> {
  return request<Goal>("/api/profile/goal");
}

export function upsertGoal(payload: GoalInput): Promise<Goal> {
  return request<Goal>("/api/profile/goal", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function createBodyMetric(payload: BodyMetricInput): Promise<BodyMetric> {
  return request<BodyMetric>("/api/body-metrics", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listBodyMetrics(): Promise<BodyMetric[]> {
  return request<BodyMetric[]>("/api/body-metrics");
}

export function previewCalorieTargets(payload: CaloriePreviewInput): Promise<CalorieTargets> {
  return request<CalorieTargets>("/api/calorie/preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export type DingTalkNotification = {
  is_configured: boolean;
  is_enabled: boolean;
  webhook_hint: string | null;
  has_signing_secret: boolean;
  keyword: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type DingTalkNotificationInput = {
  webhook: string;
  secret?: string | null;
  keyword?: string | null;
  is_enabled: boolean;
};

export function getDingTalkNotification(): Promise<DingTalkNotification> {
  return request<DingTalkNotification>("/api/notifications/dingtalk");
}

export function upsertDingTalkNotification(payload: DingTalkNotificationInput): Promise<DingTalkNotification> {
  return request<DingTalkNotification>("/api/notifications/dingtalk", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function setDingTalkNotificationEnabled(isEnabled: boolean): Promise<DingTalkNotification> {
  return request<DingTalkNotification>("/api/notifications/dingtalk/status", {
    method: "PATCH",
    body: JSON.stringify({ is_enabled: isEnabled }),
  });
}

export function deleteDingTalkNotification(): Promise<void> {
  return request<void>("/api/notifications/dingtalk", { method: "DELETE" });
}

export function sendDingTalkTestPush(): Promise<{ delivered: boolean }> {
  return request<{ delivered: boolean }>("/api/notifications/dingtalk/test", { method: "POST" });
}

export type NavKey = "home" | "records" | "plans" | "coach" | "settings";

export interface NavItem {
  key: NavKey;
  label: string;
  icon: string;
}

export interface MetricSummary {
  label: string;
  value: string;
  unit?: string;
  detail: string;
  tone: "green" | "orange" | "cream";
}

export interface DailyPlanSummary {
  goalLabel: string;
  calorieTarget: number;
  caloriesConsumed: number;
  exerciseCaloriesBurned: number;
  exerciseTarget: string;
  completionLabel: string;
}

export interface RecordSummary {
  id: string;
  category: "food" | "exercise";
  title: string;
  detail: string;
  calories: number;
  time: string;
  timestamp?: number;
}

export interface AiSuggestion {
  title: string;
  body: string;
  actionLabel: string;
}
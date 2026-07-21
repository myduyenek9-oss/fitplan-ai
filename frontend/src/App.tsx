import { useEffect, useState } from "react";
import { AppShell } from "./components/AppShell";
import { EditorialButton } from "./components/EditorialButton";
import { MetricCard } from "./components/MetricCard";
import { SectionCard } from "./components/SectionCard";
import { QuickRecordComposer } from "./features/dashboard/QuickRecordComposer";
import { ApiError, clearAccessToken, getAccessToken } from "./lib/api";
import { getDailySummary, type DailySummary, type NaturalLanguageFoodResult } from "./lib/fitplan-api";
import { getProfile } from "./lib/profile-api";
import type { AiSuggestion, DailyPlanSummary, MetricSummary, NavKey, RecordSummary } from "./lib/types";
import { CoachPage } from "./pages/CoachPage";
import { InitialSetupPage } from "./pages/InitialSetupPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { PlansPage } from "./pages/PlansPage";
import { RecordsPage } from "./pages/RecordsPage";

const initialDailyPlan: DailyPlanSummary = {
  goalLabel: "正在同步你的健康目标",
  calorieTarget: 0,
  caloriesConsumed: 0,
  exerciseTarget: "完成基础设置后，AI 会为你安排训练节奏",
  completionLabel: "等待今日记录",
};

const initialMetrics: MetricSummary[] = [
  { label: "蛋白质", value: "0", unit: "g", detail: "同步目标后显示今日完成度。", tone: "green" },
  { label: "碳水", value: "0", unit: "g", detail: "同步目标后显示今日完成度。", tone: "cream" },
  { label: "活动消耗", value: "0", unit: "kcal", detail: "记录运动后会自动汇总。", tone: "orange" },
];

const initialAiSuggestion: AiSuggestion = {
  title: "AI 今日建议",
  body: "先记录你的第一餐或一次训练。每一次真实记录，都会让接下来的建议更贴合你。",
  actionLabel: "和 AI 调整计划",
};

function localDateString(date = new Date()): string {
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 10);
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date(value));
}

function mealLabel(mealType: string | null): string {
  const labels: Record<string, string> = { breakfast: "早餐", lunch: "午餐", dinner: "晚餐", snack: "加餐" };
  return mealType ? labels[mealType] ?? "饮食" : "饮食";
}

function toRecordSummary(result: NaturalLanguageFoodResult): RecordSummary {
  const { record } = result;
  return {
    id: "food-" + record.id,
    category: "food",
    title: mealLabel(record.meal_type) + " · AI 补记",
    detail: record.original_text,
    calories: Math.round(record.calories),
    time: formatTime(record.logged_at),
  };
}

function recordsFromSummary(summary: DailySummary): RecordSummary[] {
  const food = summary.food_records.map((record) => ({
    id: "food-" + record.id,
    category: "food" as const,
    title: mealLabel(record.meal_type) + " · " + record.original_text,
    detail: "蛋白 " + Math.round(record.protein_g) + "g · 碳水 " + Math.round(record.carb_g) + "g · 脂肪 " + Math.round(record.fat_g) + "g",
    calories: Math.round(record.calories),
    time: formatTime(record.logged_at),
  }));
  const exercise = summary.exercise_records.map((record) => ({
    id: "exercise-" + record.id,
    category: "exercise" as const,
    title: "运动 · " + record.exercise_type,
    detail: record.description ?? Math.round(record.duration_minutes) + " 分钟运动记录",
    calories: -Math.round(record.calories_burned),
    time: formatTime(record.logged_at),
  }));
  return [...food, ...exercise].sort((left, right) => right.time.localeCompare(left.time));
}

function metricsFromSummary(summary: DailySummary): MetricSummary[] {
  const { food_totals: food, exercise_totals: exercise, goal } = summary;
  const proteinRemaining = Math.max(0, Math.round((goal?.protein_g ?? 0) - food.protein_g));
  const carbRemaining = Math.max(0, Math.round((goal?.carb_g ?? 0) - food.carb_g));
  return [
    { label: "蛋白质", value: String(Math.round(food.protein_g)), unit: "g", detail: goal ? "距离目标还差 " + proteinRemaining + "g。" : "完成目标设置后会显示建议。", tone: "green" },
    { label: "碳水", value: String(Math.round(food.carb_g)), unit: "g", detail: goal ? "距离目标还差 " + carbRemaining + "g。" : "完成目标设置后会显示建议。", tone: "cream" },
    { label: "活动消耗", value: String(Math.round(exercise.calories_burned)), unit: "kcal", detail: exercise.duration_minutes > 0 ? "今天已运动 " + Math.round(exercise.duration_minutes) + " 分钟。" : "记录运动后会自动汇总。", tone: "orange" },
  ];
}

export type DashboardPreviewProps = {
  onNeedSetup?: () => void;
  onNavigate?: (key: NavKey) => void;
};

export function DashboardPreview({ onNeedSetup, onNavigate }: DashboardPreviewProps) {
  const [dailyPlan, setDailyPlan] = useState(initialDailyPlan);
  const [remainingCalories, setRemainingCalories] = useState(0);
  const [metrics, setMetrics] = useState(initialMetrics);
  const [records, setRecords] = useState<RecordSummary[]>([]);
  const [aiSuggestion, setAiSuggestion] = useState(initialAiSuggestion);
  const [hasGoal, setHasGoal] = useState<boolean | null>(null);
  const [dailyError, setDailyError] = useState<string | null>(null);

  function applyDailySummary(summary: DailySummary, adjustmentSuggestion?: string) {
    const calorieTarget = Math.round(summary.goal?.daily_calories ?? 0);
    const caloriesConsumed = Math.round(summary.food_totals.calories);
    const completion = calorieTarget > 0 ? Math.round((caloriesConsumed / calorieTarget) * 100) : 0;
    setHasGoal(Boolean(summary.goal));
    setDailyPlan({
      goalLabel: summary.goal ? "每日目标 · " + calorieTarget + " kcal" : "还没有设置每日目标",
      calorieTarget,
      caloriesConsumed,
      exerciseTarget: summary.exercise_totals.duration_minutes > 0 ? "今天已完成 " + Math.round(summary.exercise_totals.duration_minutes) + " 分钟运动" : "今天安排一段你愿意开始的轻运动",
      completionLabel: calorieTarget > 0 ? "今日完成 " + completion + "%" : "等待设置目标",
    });
    setRemainingCalories(Math.round(summary.remaining_calories ?? 0));
    setMetrics(metricsFromSummary(summary));
    setRecords(recordsFromSummary(summary));
    if (adjustmentSuggestion) setAiSuggestion((current) => ({ ...current, body: adjustmentSuggestion }));
  }

  useEffect(() => {
    let isCurrent = true;
    void getDailySummary(localDateString())
      .then((summary) => { if (isCurrent) { applyDailySummary(summary); setDailyError(null); } })
      .catch((error: unknown) => { if (isCurrent) setDailyError(error instanceof Error ? error.message : "无法同步今日记录，请稍后重试。"); });
    return () => { isCurrent = false; };
  }, []);

  function handleFoodRecorded(result: NaturalLanguageFoodResult) {
    applyDailySummary(result.daily_summary, result.adjustment_suggestion);
    setRecords((current) => current.length > 0 ? current : [toRecordSummary(result)]);
  }

  if (hasGoal === false) {
    return <AppShell activeNav="settings" onNavigate={onNavigate} eyebrow="开始前的一小步" subtitle="先建立每日热量和营养素目标" title="让计划从你的真实数据开始"><section className="dashboard-setup-prompt"><span aria-hidden="true">✦</span><p>还没有找到你的每日目标。填写体重、活动水平和健身方向后，FitPlan AI 才能正确计算每餐余量与训练消耗。</p><EditorialButton variant="accent" onClick={onNeedSetup}>设置我的目标</EditorialButton></section></AppShell>;
  }

  return <AppShell activeNav="home" onNavigate={onNavigate} eyebrow="今日 · 轻盈记录" subtitle={dailyPlan.goalLabel} title="今天离目标更近一点">
    <div className="dashboard-preview"><div className="dashboard-preview__main">
      {dailyError ? <p className="dashboard-preview__error" role="alert">{dailyError}</p> : null}
      <section className="daily-hero" aria-label="今日计划概览"><div className="daily-hero__copy"><p className="daily-hero__label">今日计划</p><p className="daily-hero__calories">{dailyPlan.calorieTarget} kcal</p><p className="daily-hero__target">{dailyPlan.exerciseTarget}</p></div><div className="daily-hero__stats" aria-label="热量进度"><div><span>已摄入</span><strong>{dailyPlan.caloriesConsumed}</strong></div><div><span>剩余</span><strong>{remainingCalories}</strong></div><div><span>状态</span><strong>{dailyPlan.completionLabel}</strong></div></div><div className="quick-actions" aria-label="快捷操作"><EditorialButton variant="accent" onClick={() => onNavigate?.("records")}>记录饮食</EditorialButton><EditorialButton variant="secondary" onClick={() => onNavigate?.("records")}>记录运动</EditorialButton><EditorialButton onClick={() => onNavigate?.("coach")}>和 AI 调整计划</EditorialButton></div></section>
      <div className="metric-card-grid" aria-label="核心指标">{metrics.map((metric) => <MetricCard key={metric.label} {...metric} />)}</div>
      <SectionCard title="今日计划的记录" subtitle="饮食和运动会自动汇总到每日热量里">{records.length > 0 ? <div className="record-list">{records.map((record) => <article className="record-row" key={record.id}><div className={"record-row__icon record-row__icon--" + record.category} aria-hidden="true">{record.category === "food" ? "🍽" : "🏃"}</div><div className="record-row__content"><h3>{record.title}</h3><p>{record.detail}</p></div><div className="record-row__meta"><span>{record.time}</span><strong>{record.calories > 0 ? "+" : ""}{record.calories} kcal</strong></div></article>)}</div> : <p className="dashboard-empty-records">今天还没有记录。从右侧告诉 AI 你吃了什么，或完成一条运动记录。</p>}</SectionCard>
    </div><aside className="dashboard-preview__side" aria-label="AI 调整建议"><QuickRecordComposer date={localDateString()} onRecorded={handleFoodRecorded} /><SectionCard title={aiSuggestion.title} subtitle="根据今天记录，给出更容易坚持的调整" action={<EditorialButton variant="secondary" onClick={() => onNavigate?.("coach")}>{aiSuggestion.actionLabel}</EditorialButton>}><div className="ai-suggestion"><p>{aiSuggestion.body}</p><div className="ai-suggestion__chips" aria-label="推荐重点"><span>高蛋白</span><span>低油脂</span><span>饱腹感</span></div></div></SectionCard></aside></div>
  </AppShell>;
}

type AppScreen = "auth" | "checking" | "setup" | "dashboard";
function App() {
  const [screen, setScreen] = useState<AppScreen>(() => getAccessToken() ? "checking" : "auth");
  const [activeNav, setActiveNav] = useState<NavKey>("home");

  useEffect(() => {
    if (screen !== "checking") return;
    let isCurrent = true;
    void getProfile()
      .then(() => { if (isCurrent) setScreen("dashboard"); })
      .catch((error: unknown) => {
        if (!isCurrent) return;
        if (error instanceof ApiError && error.status === 404) { setScreen("setup"); return; }
        clearAccessToken();
        setScreen("auth");
      });
    return () => { isCurrent = false; };
  }, [screen]);

  function navigate(key: NavKey) {
    if (key === "settings") { setScreen("setup"); return; }
    setActiveNav(key);
  }

  if (screen === "auth") return <OnboardingPage onAuthenticated={() => setScreen("checking")} />;
  if (screen === "checking") return <main className="app-loading" aria-live="polite">正在打开你的健康档案…</main>;
  if (screen === "setup") return <InitialSetupPage onCompleted={() => { setActiveNav("home"); setScreen("dashboard"); }} />;
  if (activeNav === "records") return <RecordsPage onNavigate={navigate} />;
  if (activeNav === "plans") return <PlansPage onNavigate={navigate} />;
  if (activeNav === "coach") return <CoachPage onNavigate={navigate} />;
  return <DashboardPreview onNeedSetup={() => setScreen("setup")} onNavigate={navigate} />;
}

export default App;

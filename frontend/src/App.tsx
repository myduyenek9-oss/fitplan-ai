import { useEffect, useState } from "react";
import { AppShell } from "./components/AppShell";
import { EditorialButton } from "./components/EditorialButton";
import { MetricCard } from "./components/MetricCard";
import { ProgressInsights } from "./components/ProgressInsights";
import { SectionCard } from "./components/SectionCard";
import { QuickRecordComposer } from "./features/dashboard/QuickRecordComposer";
import { ApiError, clearAccessToken, getAccessToken } from "./lib/api";
import { getDailySummary, type DailySummary, type ExerciseRecord, type FoodRecord, type NaturalLanguageFoodResult } from "./lib/fitplan-api";
import { getProfile } from "./lib/profile-api";
import { sendChatMessage } from "./lib/chat-api";
import { formatRecordTime, getRecordDisplayTimestamp } from "./lib/record-time";
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
  exerciseCaloriesBurned: 0,
  exerciseTarget: "完成基础设置后，AI 会为你安排训练节奏",
  completionLabel: "等待今日记录",
};

const initialMetrics: MetricSummary[] = [
  { label: "蛋白质", value: "0", unit: "g", detail: "同步目标后显示今日完成度。", tone: "green" },
  { label: "碳水", value: "0", unit: "g", detail: "同步目标后显示今日完成度。", tone: "cream" },
  { label: "脂肪", value: "0", unit: "g", detail: "同步目标后显示今日完成度。", tone: "orange" },
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

function mealLabel(mealType: string | null): string {
  const labels: Record<string, string> = { breakfast: "早餐", lunch: "午餐", dinner: "晚餐", snack: "加餐" };
  return mealType ? labels[mealType] ?? "饮食" : "饮食";
}

function isExerciseRecord(record: FoodRecord | ExerciseRecord): record is ExerciseRecord {
  return "calories_burned" in record;
}

function toRecordSummary(result: NaturalLanguageFoodResult): RecordSummary {
  const { record } = result;
  if (isExerciseRecord(record)) {
    return {
      id: "exercise-" + record.id,
      category: "exercise",
      title: "运动 ? " + record.exercise_type,
      detail: record.description ?? Math.round(record.duration_minutes) + " \u5206\u949f运动\u8bb0\u5f55",
      calories: -Math.round(record.calories_burned),
      time: formatRecordTime({ loggedAt: record.logged_at }),
      timestamp: getRecordDisplayTimestamp({ loggedAt: record.logged_at }),
    };
  }
  return {
    id: "food-" + record.id,
    category: "food",
    title: mealLabel(record.meal_type) + " ? AI 补记",
    detail: record.original_text,
    calories: Math.round(record.calories),
    time: formatRecordTime({
      loggedAt: record.logged_at,
      createdAt: record.created_at,
      sourceText: record.original_text,
      preferCreatedAtForRoundedAiTime: record.parsed_content.source === "ai",
    }),
    timestamp: getRecordDisplayTimestamp({ loggedAt: record.logged_at, createdAt: record.created_at, sourceText: record.original_text, preferCreatedAtForRoundedAiTime: record.parsed_content.source === "ai" }),
  };
}

function recordsFromSummary(summary: DailySummary): RecordSummary[] {
  const food = summary.food_records.map((record) => ({
    id: "food-" + record.id,
    category: "food" as const,
    title: mealLabel(record.meal_type) + " · " + record.original_text,
    detail: "蛋白 " + Math.round(record.protein_g) + "g · 碳水 " + Math.round(record.carb_g) + "g · 脂肪 " + Math.round(record.fat_g) + "g",
    calories: Math.round(record.calories),
    time: formatRecordTime({
      loggedAt: record.logged_at,
      createdAt: record.created_at,
      sourceText: record.original_text,
      preferCreatedAtForRoundedAiTime: record.parsed_content.source === "ai",
    }),
    timestamp: getRecordDisplayTimestamp({ loggedAt: record.logged_at, createdAt: record.created_at, sourceText: record.original_text, preferCreatedAtForRoundedAiTime: record.parsed_content.source === "ai" }),
  }));
  const exercise = summary.exercise_records.map((record) => ({
    id: "exercise-" + record.id,
    category: "exercise" as const,
    title: "运动 · " + record.exercise_type,
    detail: record.description ?? Math.round(record.duration_minutes) + " 分钟运动记录",
    calories: -Math.round(record.calories_burned),
    time: formatRecordTime({ loggedAt: record.logged_at }),
    timestamp: getRecordDisplayTimestamp({ loggedAt: record.logged_at }),
  }));
  return [...food, ...exercise].sort((left, right) => (left.timestamp ?? 0) - (right.timestamp ?? 0));
}

function metricsFromSummary(summary: DailySummary): MetricSummary[] {
  const { food_totals: food, goal } = summary;
  const proteinRemaining = Math.max(0, Math.round((goal?.protein_g ?? 0) - food.protein_g));
  const carbRemaining = Math.max(0, Math.round((goal?.carb_g ?? 0) - food.carb_g));
  const fatRemaining = Math.max(0, Math.round((goal?.fat_g ?? 0) - food.fat_g));
  return [
    { label: "蛋白质", value: String(Math.round(food.protein_g)), unit: "g", detail: goal ? "距离目标还差 " + proteinRemaining + "g。" : "完成目标设置后会显示建议。", tone: "green" },
    { label: "碳水", value: String(Math.round(food.carb_g)), unit: "g", detail: goal ? "距离目标还差 " + carbRemaining + "g。" : "完成目标设置后会显示建议。", tone: "cream" },
    { label: "脂肪", value: String(Math.round(food.fat_g)), unit: "g", detail: goal ? "距离目标还差 " + fatRemaining + "g。" : "完成目标设置后会显示建议。", tone: "orange" },
  ];
}

export type DashboardPreviewProps = {
  onNeedSetup?: () => void;
  onNavigate?: (key: NavKey) => void;
  saveNotice?: string | null;
};

export function DashboardPreview({ onNeedSetup, onNavigate, saveNotice }: DashboardPreviewProps) {
  const [dailyPlan, setDailyPlan] = useState(initialDailyPlan);
  const [remainingCalories, setRemainingCalories] = useState(0);
  const [metrics, setMetrics] = useState(initialMetrics);
  const [records, setRecords] = useState<RecordSummary[]>([]);
  const [aiSuggestion, setAiSuggestion] = useState(initialAiSuggestion);
  const [hasGoal, setHasGoal] = useState<boolean | null>(null);
  const [dailyError, setDailyError] = useState<string | null>(null);
  const [isAdoptingSuggestion, setIsAdoptingSuggestion] = useState(false);
  const [adoptionNotice, setAdoptionNotice] = useState<string | null>(null);

  function applyDailySummary(summary: DailySummary, adjustmentSuggestion?: string) {
    const calorieTarget = Math.round(summary.goal?.daily_calories ?? 0);
    const caloriesConsumed = Math.round(summary.food_totals.calories);
    const completion = calorieTarget > 0 ? Math.round((caloriesConsumed / calorieTarget) * 100) : 0;
    setHasGoal(Boolean(summary.goal));
    setDailyPlan({
      goalLabel: summary.goal ? "每日目标 · " + calorieTarget + " kcal" : "还没有设置每日目标",
      calorieTarget,
      caloriesConsumed,
      exerciseCaloriesBurned: Math.round(summary.exercise_totals.calories_burned),

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

  async function adoptSuggestion() {
    if (isAdoptingSuggestion) return;
    setIsAdoptingSuggestion(true);
    setAdoptionNotice(null);
    try {
      const result = await sendChatMessage(`\u8bf7\u91c7\u7eb3\u4eca\u5929\u7684 AI \u5efa\u8bae\uff0c\u5e76\u6839\u636e\u6211\u7684\u771f\u5b9e\u8bb0\u5f55\u8c03\u6574\u63a5\u4e0b\u6765 7 \u5929\u8ba1\u5212\uff1b\u5982\u679c\u5efa\u8bae\u9002\u7528\uff0c\u8bf7\u76f4\u63a5\u4fdd\u5b58\u8c03\u6574\u7ed3\u679c\u3002\u5f53\u524d\u5efa\u8bae\uff1a${aiSuggestion.body}`, localDateString());
      if (result.daily_summary) applyDailySummary(result.daily_summary, result.reply);
      setAdoptionNotice(result.plan_adjustment?.status === "applied" ? "\u8ba1\u5212\u5df2\u6839\u636e\u4eca\u5929\u7684\u5efa\u8bae\u66f4\u65b0\u5e76\u4fdd\u5b58\u3002" : "AI \u5df2\u6536\u5230\u5efa\u8bae\uff0c\u4f60\u53ef\u4ee5\u7ee7\u7eed\u548c\u5b83\u6c9f\u901a\u5177\u4f53\u8c03\u6574\u3002");
    } catch (error) {
      setAdoptionNotice(error instanceof Error ? error.message : "\u6682\u65f6\u65e0\u6cd5\u91c7\u7eb3\u5efa\u8bae\uff0c\u8bf7\u7a0d\u540e\u518d\u8bd5\u3002");
    } finally {
      setIsAdoptingSuggestion(false);
    }
  }

  if (hasGoal === false) {
    return <AppShell activeNav="settings" onNavigate={onNavigate} eyebrow="开始前的一小步" subtitle="先建立每日热量和营养素目标" title="让计划从你的真实数据开始"><section className="dashboard-setup-prompt"><span aria-hidden="true">✦</span><p>还没有找到你的每日目标。填写体重、活动水平和健身方向后，FitPlan AI 才能正确计算每餐余量与训练消耗。</p><EditorialButton variant="accent" onClick={onNeedSetup}>设置我的目标</EditorialButton></section></AppShell>;
  }

  return <AppShell activeNav="home" onNavigate={onNavigate} eyebrow="今日 · 轻盈记录" subtitle={dailyPlan.goalLabel} title="今天离目标更近一点">
    <div className="dashboard-preview">
      <div className="dashboard-preview__main">
        {saveNotice ? <p className="dashboard-preview__success" role="status">{saveNotice}</p> : null}
        {dailyError ? <p className="dashboard-preview__error" role="alert">{dailyError}</p> : null}
        <section className="daily-hero" aria-label="今日计划概览">
          <div className="daily-hero__copy"><p className="daily-hero__label">今日计划</p><p className="daily-hero__calories">{dailyPlan.calorieTarget} kcal</p><p className="daily-hero__target">{dailyPlan.exerciseTarget}</p></div>
          <div className="daily-hero__stats" aria-label="热量进度"><div><span>已摄入</span><strong>{dailyPlan.caloriesConsumed}</strong></div><div><span>剩余</span><strong>{remainingCalories}</strong></div><div><span>运动消耗</span><strong>{dailyPlan.exerciseCaloriesBurned}</strong></div><div><span>状态</span><strong>{dailyPlan.completionLabel}</strong></div></div>
          <details className="calorie-calculation"><summary>剩余热量怎么算？</summary><p>{dailyPlan.calorieTarget} - {dailyPlan.caloriesConsumed} + {dailyPlan.exerciseCaloriesBurned} = {remainingCalories} kcal</p><small>运动消耗会全部计入今天的可摄入额度，但运动热量只是估算值，请把它当作参考。</small></details>
          <div className="quick-actions" aria-label="快捷操作"><EditorialButton variant="dingtalk-action" onClick={() => onNavigate?.("records")}>记录饮食</EditorialButton><EditorialButton variant="dingtalk-action" onClick={() => onNavigate?.("records")}>记录运动</EditorialButton><EditorialButton variant="dingtalk-action" onClick={() => onNavigate?.("coach")}>和 AI 调整计划</EditorialButton></div>
        </section>
        <div className="metric-card-grid" aria-label="核心指标">{metrics.map((metric) => <MetricCard key={metric.label} {...metric} />)}</div>
        <SectionCard title="今日计划的记录" subtitle="饮食和运动会自动汇总到每日热量">{records.length > 0 ? <div className="record-list">{records.map((record) => <article className="record-row" key={record.id}><div className={"record-row__icon record-row__icon--" + record.category} aria-hidden="true">{record.category === "food" ? "🍽" : "🏃"}</div><div className="record-row__content"><h3>{record.title}</h3><p>{record.detail}</p></div><div className="record-row__meta"><span>{record.time}</span><strong>{record.calories > 0 ? "+" : ""}{record.calories} kcal</strong></div></article>)}</div> : <p className="dashboard-empty-records">今天还没有记录。从右侧告诉 AI 你吃了什么，或完成一条运动记录。</p>}</SectionCard>
        <ProgressInsights />
      </div>
      <aside className="dashboard-preview__side" aria-label="AI 调整建议">
        <QuickRecordComposer date={localDateString()} onRecorded={handleFoodRecorded} />
        <SectionCard title={aiSuggestion.title} subtitle="根据今天记录，给出更容易坚持的调整" action={<div className="ai-suggestion__actions"><EditorialButton variant="dingtalk-action" loading={isAdoptingSuggestion} loadingLabel="正在调整…" onClick={() => void adoptSuggestion()}>采纳并调整计划</EditorialButton><EditorialButton variant="dingtalk-action" onClick={() => onNavigate?.("coach")}>{aiSuggestion.actionLabel}</EditorialButton></div>}>
          <div className="ai-suggestion">{adoptionNotice ? <p className="dashboard-preview__success" role="status">{adoptionNotice}</p> : null}<p>{aiSuggestion.body}</p><div className="ai-suggestion__chips" aria-label="推荐重点"><span>高蛋白</span><span>低油脂</span><span>饱腹感</span></div></div>
        </SectionCard>
      </aside>
    </div>
  </AppShell>;
}

type AppScreen = "auth" | "checking" | "setup" | "settings" | "dashboard";
function App() {
  const [screen, setScreen] = useState<AppScreen>(() => getAccessToken() ? "checking" : "auth");
  const [activeNav, setActiveNav] = useState<NavKey>("home");
  const [saveNotice, setSaveNotice] = useState<string | null>(null);

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
    if (key === "settings") { setScreen("settings"); return; }
    setActiveNav(key);
    setScreen("dashboard");
  }

  if (screen === "auth") return <OnboardingPage onAuthenticated={() => setScreen("checking")} />;
  if (screen === "checking") return <main className="app-loading" aria-live="polite">正在打开你的健康档案…</main>;
  if (screen === "setup") return <InitialSetupPage onCompleted={() => { setActiveNav("home"); setScreen("dashboard"); }} />;
  if (screen === "settings") return <AppShell activeNav="settings" onNavigate={navigate} eyebrow="个人中心" title="我的" subtitle="管理健康资料、目标和每日通知"><InitialSetupPage embedded isEditing onCompleted={() => { setActiveNav("home"); setSaveNotice("资料已保存，今日计划已同步更新。"); setScreen("dashboard"); }} onLogout={() => { clearAccessToken(); setSaveNotice(null); setActiveNav("home"); setScreen("auth"); }} /></AppShell>;
  if (activeNav === "records") return <RecordsPage onNavigate={navigate} />;
  if (activeNav === "plans") return <PlansPage onNavigate={navigate} />;
  if (activeNav === "coach") return <CoachPage onNavigate={navigate} />;
  return <DashboardPreview onNeedSetup={() => setScreen("setup")} onNavigate={navigate} saveNotice={saveNotice} />;
}

export default App;

import { useState } from "react";
import { AppShell } from "./components/AppShell";
import { EditorialButton } from "./components/EditorialButton";
import { MetricCard } from "./components/MetricCard";
import { SectionCard } from "./components/SectionCard";
import { QuickRecordComposer } from "./features/dashboard/QuickRecordComposer";
import type { NaturalLanguageFoodResult } from "./lib/fitplan-api";
import { getAccessToken } from "./lib/api";
import { OnboardingPage } from "./pages/OnboardingPage";
import type { AiSuggestion, DailyPlanSummary, MetricSummary, RecordSummary } from "./lib/types";

const initialDailyPlan: DailyPlanSummary = {
  goalLabel: "减脂 · 轻强度训练周",
  calorieTarget: 1850,
  caloriesConsumed: 1280,
  exerciseTarget: "快走 30 分钟 + 上肢训练",
  completionLabel: "今日完成 69%",
};

const metrics: MetricSummary[] = [
  {
    label: "蛋白质",
    value: "92",
    unit: "g",
    detail: "距离目标还差 28g，晚餐优先鸡胸/鱼虾。",
    tone: "green",
  },
  {
    label: "饮水",
    value: "1.6",
    unit: "L",
    detail: "下午再补 800ml，训练前小口喝。",
    tone: "cream",
  },
  {
    label: "活动消耗",
    value: "410",
    unit: "kcal",
    detail: "快走完成后预计再增加 160 kcal。",
    tone: "orange",
  },
];

const initialRecords: RecordSummary[] = [
  {
    id: "breakfast",
    category: "food",
    title: "早餐 · 燕麦酸奶碗",
    detail: "燕麦 45g、希腊酸奶、蓝莓和少量坚果",
    calories: 420,
    time: "08:20",
  },
  {
    id: "lunch",
    category: "food",
    title: "午餐 · 鸡胸能量盘",
    detail: "糙米饭、鸡胸肉、彩椒和西兰花",
    calories: 620,
    time: "12:35",
  },
  {
    id: "walk",
    category: "exercise",
    title: "运动 · 午后快走",
    detail: "中等配速 22 分钟，心率稳定",
    calories: -180,
    time: "15:10",
  },
];

const initialAiSuggestion: AiSuggestion = {
  title: "AI 晚餐建议",
  body: "如果晚餐想吃得满足，可以选择番茄牛肉汤 + 半份杂粮饭 + 一盘绿叶菜，控制油脂的同时把蛋白质补够。",
  actionLabel: "让 AI 重新细化",
};

function localDateString(date = new Date()): string {
  const timezoneOffsetMs = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - timezoneOffsetMs).toISOString().slice(0, 10);
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

function mealLabel(mealType: string | null): string {
  const labels: Record<string, string> = {
    breakfast: "早餐",
    lunch: "午餐",
    dinner: "晚餐",
    snack: "加餐",
  };
  return mealType ? (labels[mealType] ?? "饮食") : "饮食";
}

function toRecordSummary(result: NaturalLanguageFoodResult): RecordSummary {
  const { record } = result;
  return {
    id: `food-${record.id}`,
    category: "food",
    title: `${mealLabel(record.meal_type)} · AI 补记`,
    detail: record.original_text,
    calories: Math.round(record.calories),
    time: formatTime(record.logged_at),
  };
}

export function DashboardPreview() {
  const [dailyPlan, setDailyPlan] = useState(initialDailyPlan);
  const [remainingCalories, setRemainingCalories] = useState(
    initialDailyPlan.calorieTarget - initialDailyPlan.caloriesConsumed,
  );
  const [records, setRecords] = useState(initialRecords);
  const [aiSuggestion, setAiSuggestion] = useState(initialAiSuggestion);

  function handleFoodRecorded(result: NaturalLanguageFoodResult) {
    const { daily_summary: summary } = result;
    const calorieTarget = summary.goal?.daily_calories ?? dailyPlan.calorieTarget;
    const caloriesConsumed = Math.round(summary.food_totals.calories);
    const completion = calorieTarget > 0 ? Math.round((caloriesConsumed / calorieTarget) * 100) : 0;

    setDailyPlan((current) => ({
      ...current,
      calorieTarget,
      caloriesConsumed,
      completionLabel: `今日完成 ${completion}%`,
    }));
    setRemainingCalories(
      Math.round(summary.remaining_calories ?? Math.max(calorieTarget - caloriesConsumed, 0)),
    );
    setRecords((current) => [toRecordSummary(result), ...current]);
    setAiSuggestion((current) => ({ ...current, body: result.adjustment_suggestion }));
  }

  return (
    <AppShell
      activeNav="home"
      eyebrow="今日 · 轻盈记录"
      subtitle={dailyPlan.goalLabel}
      title="今天离目标更近一点"
    >
      <div className="dashboard-preview">
        <div className="dashboard-preview__main">
          <section className="daily-hero" aria-label="今日计划概览">
            <div className="daily-hero__copy">
              <p className="daily-hero__label">今日计划</p>
              <p className="daily-hero__calories">{dailyPlan.calorieTarget} kcal</p>
              <p className="daily-hero__target">{dailyPlan.exerciseTarget}</p>
            </div>

            <div className="daily-hero__stats" aria-label="热量进度">
              <div>
                <span>已摄入</span>
                <strong>{dailyPlan.caloriesConsumed}</strong>
              </div>
              <div>
                <span>剩余</span>
                <strong>{remainingCalories}</strong>
              </div>
              <div>
                <span>状态</span>
                <strong>{dailyPlan.completionLabel}</strong>
              </div>
            </div>

            <div className="quick-actions" aria-label="快捷操作">
              <EditorialButton variant="accent">记录饮食</EditorialButton>
              <EditorialButton variant="secondary">记录运动</EditorialButton>
              <EditorialButton>和 AI 调整计划</EditorialButton>
            </div>
          </section>

          <div className="metric-card-grid" aria-label="核心指标">
            {metrics.map((metric) => (
              <MetricCard key={metric.label} {...metric} />
            ))}
          </div>

          <SectionCard title="今日计划的记录" subtitle="饮食和运动会自动汇总到每日热量里">
            <div className="record-list">
              {records.map((record) => (
                <article className="record-row" key={record.id}>
                  <div className={`record-row__icon record-row__icon--${record.category}`} aria-hidden="true">
                    {record.category === "food" ? "🍽" : "🏃"}
                  </div>
                  <div className="record-row__content">
                    <h3>{record.title}</h3>
                    <p>{record.detail}</p>
                  </div>
                  <div className="record-row__meta">
                    <span>{record.time}</span>
                    <strong>
                      {record.calories > 0 ? "+" : ""}
                      {record.calories} kcal
                    </strong>
                  </div>
                </article>
              ))}
            </div>
          </SectionCard>
        </div>

        <aside className="dashboard-preview__side" aria-label="AI 调整建议">
          <QuickRecordComposer date={localDateString()} onRecorded={handleFoodRecorded} />
          <SectionCard
            title={aiSuggestion.title}
            subtitle="根据今天记录，给出更容易坚持的调整"
            action={<EditorialButton variant="secondary">{aiSuggestion.actionLabel}</EditorialButton>}
          >
            <div className="ai-suggestion">
              <p>{aiSuggestion.body}</p>
              <div className="ai-suggestion__chips" aria-label="推荐重点">
                <span>高蛋白</span>
                <span>低油脂</span>
                <span>饱腹感</span>
              </div>
            </div>
          </SectionCard>
        </aside>
      </div>
    </AppShell>
  );
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => Boolean(getAccessToken()));

  if (!isAuthenticated) {
    return <OnboardingPage onAuthenticated={() => setIsAuthenticated(true)} />;
  }

  return <DashboardPreview />;
}

export default App;

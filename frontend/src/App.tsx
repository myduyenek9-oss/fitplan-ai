import { AppShell } from "./components/AppShell";
import { EditorialButton } from "./components/EditorialButton";
import { MetricCard } from "./components/MetricCard";
import { SectionCard } from "./components/SectionCard";
import type { AiSuggestion, DailyPlanSummary, MetricSummary, RecordSummary } from "./lib/types";

const dailyPlan: DailyPlanSummary = {
  goalLabel: "减脂 · 轻强度训练周",
  calorieTarget: 1850,
  caloriesConsumed: 1280,
  exerciseTarget: "快走 30 分钟 + 上肢训练",
  completionLabel: "今日完成 69%",
};

const remainingCalories = dailyPlan.calorieTarget - dailyPlan.caloriesConsumed;

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

const records: RecordSummary[] = [
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

const aiSuggestion: AiSuggestion = {
  title: "AI 晚餐建议",
  body: "如果晚餐想吃得满足，可以选择番茄牛肉汤 + 半份杂粮饭 + 一盘绿叶菜，控制油脂的同时把蛋白质补够。",
  actionLabel: "让 AI 重新细化",
};

function App() {
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
                    <strong>{record.calories > 0 ? "+" : ""}{record.calories} kcal</strong>
                  </div>
                </article>
              ))}
            </div>
          </SectionCard>
        </div>

        <aside className="dashboard-preview__side" aria-label="AI 调整建议">
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

export default App;

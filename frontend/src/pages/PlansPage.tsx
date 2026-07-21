import { useEffect, useState } from "react";
import { AppShell } from "../components/AppShell";
import { EditorialButton } from "../components/EditorialButton";
import { SectionCard } from "../components/SectionCard";
import { ApiError } from "../lib/api";
import { generatePlan, getCurrentPlan, type FitnessPlan, type PlanDay } from "../lib/plan-api";
import type { NavKey } from "../lib/types";

export type PlansPageProps = {
  onNavigate: (key: NavKey) => void;
};

function localDateString(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

function shortDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", { weekday: "short", month: "numeric", day: "numeric" }).format(new Date(value + "T00:00:00"));
}

function mealTypeLabel(value: string | null): string {
  const labels: Record<string, string> = { breakfast: "早餐", lunch: "午餐", dinner: "晚餐", snack: "加餐" };
  return value ? labels[value] ?? "饮食" : "饮食";
}

function planError(error: unknown): string {
  return error instanceof Error ? error.message : "暂时无法读取计划，请稍后再试。";
}

function PlanDayDetail({ day }: { day: PlanDay }) {
  const training = day.training_instruction;
  return (
    <>
      <section className="plan-day-overview" aria-label={`${shortDate(day.date)} 计划概览`}>
        <div>
          <p>当日热量目标</p>
          <strong>{Math.round(day.calorie_target)} <small>kcal</small></strong>
        </div>
        <div>
          <p>{training.kind === "rest" ? "恢复安排" : "训练安排"}</p>
          <strong className="plan-day-overview__workout">{training.title}</strong>
          {training.duration_minutes ? <span>{Math.round(training.duration_minutes)} 分钟</span> : null}
        </div>
      </section>

      <div className="plan-meal-list" aria-label="饮食安排">
        {day.meals.map((meal, index) => (
          <article className="plan-meal" key={`${meal.name}-${index}`}>
            <p className="plan-meal__type">{mealTypeLabel(meal.meal_type)}</p>
            <div className="plan-meal__content">
              <h3>{meal.name}</h3>
              <p>蛋白 {Math.round(meal.protein_g)}g · 碳水 {Math.round(meal.carb_g)}g · 脂肪 {Math.round(meal.fat_g)}g</p>
            </div>
            <strong>{Math.round(meal.calories)} kcal</strong>
          </article>
        ))}
      </div>

      <section className={`plan-training plan-training--${training.kind}`} aria-label="训练细节">
        <span aria-hidden="true">{training.kind === "rest" ? "☼" : "↗"}</span>
        <div>
          <p>{training.kind === "rest" ? "恢复日" : "今日训练"}</p>
          <h3>{training.title}</h3>
          <div>{training.instructions}</div>
        </div>
      </section>
    </>
  );
}

export function PlansPage({ onNavigate }: PlansPageProps) {
  const [plan, setPlan] = useState<FitnessPlan | null>(null);
  const [selectedDay, setSelectedDay] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let current = true;
    void getCurrentPlan()
      .then((result) => { if (current) { setPlan(result); setSelectedDay(0); } })
      .catch((nextError: unknown) => {
        if (!current) return;
        if (nextError instanceof ApiError && nextError.status === 404) setPlan(null);
        else setError(planError(nextError));
      })
      .finally(() => { if (current) setIsLoading(false); });
    return () => { current = false; };
  }, []);

  async function createPlan() {
    if (isGenerating) return;
    setIsGenerating(true);
    setError(null);
    try {
      const generated = await generatePlan(localDateString());
      setPlan(generated);
      setSelectedDay(0);
    } catch (nextError) {
      setError(planError(nextError));
    } finally {
      setIsGenerating(false);
    }
  }

  const day = plan?.days[selectedDay];
  return (
    <AppShell activeNav="plans" onNavigate={onNavigate} eyebrow="每周节奏 · 可继续调整" title="你的 7 天计划" subtitle="饮食与训练会根据目标、记录和你与 AI 的交流持续更新。">
      {error ? <p className="dashboard-preview__error" role="alert">{error}</p> : null}
      {isLoading ? <p className="page-inline-loading" aria-live="polite">正在读取你的计划…</p> : null}
      {!isLoading && !plan ? (
        <section className="plan-empty">
          <span aria-hidden="true">✦</span>
          <p className="plan-empty__eyebrow">从第一周开始</p>
          <h2>让 AI 按你的目标排好接下来的 7 天</h2>
          <p>它会结合你的热量、三大营养素与运动方向，生成可执行的饮食和训练安排。之后任何临时变化都可以继续对话调整。</p>
          <EditorialButton variant="accent" loading={isGenerating} loadingLabel="正在生成 7 天计划…" onClick={createPlan}>生成我的 7 天计划</EditorialButton>
        </section>
      ) : null}
      {plan && day ? (
        <div className="plans-page">
          <section className="plan-header-card">
            <div>
              <p>正在执行</p>
              <h2>{plan.title}</h2>
              <span>{shortDate(plan.start_date)} — {shortDate(plan.end_date)}</span>
            </div>
            <EditorialButton variant="secondary" loading={isGenerating} loadingLabel="正在更新…" onClick={createPlan}>重新生成</EditorialButton>
          </section>
          <div className="plan-day-tabs" role="tablist" aria-label="选择计划日期">
            {plan.days.map((item, index) => <button key={item.date} type="button" role="tab" aria-selected={selectedDay === index} className={selectedDay === index ? "is-active" : ""} onClick={() => setSelectedDay(index)}><span>第 {index + 1} 天</span><strong>{shortDate(item.date)}</strong></button>)}
          </div>
          <SectionCard title={shortDate(day.date) + " 的安排"} subtitle="不需要完美执行，完成大部分就已经很好。">
            <PlanDayDetail day={day} />
          </SectionCard>
          <section className="plan-ai-cta">
            <div><p>临时吃多了、没时间训练或想换食材？</p><strong>直接和 AI 说，它会帮你调整而不是让你重来。</strong></div>
            <EditorialButton variant="accent" onClick={() => onNavigate("coach")}>和 AI 调整计划</EditorialButton>
          </section>
        </div>
      ) : null}
    </AppShell>
  );
}

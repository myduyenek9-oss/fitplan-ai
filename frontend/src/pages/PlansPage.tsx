import { useEffect, useState } from "react";
import { AppShell } from "../components/AppShell";
import { EditorialButton } from "../components/EditorialButton";
import { SectionCard } from "../components/SectionCard";
import { ApiError } from "../lib/api";
import { generatePlan, getCurrentPlan, postponePlanDay, type FitnessPlan, type PlanDay } from "../lib/plan-api";
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

function todayPlanIndex(days: PlanDay[]): number {
  const today = localDateString();
  const index = days.findIndex((item) => item.date === today);
  return index >= 0 ? index : 0;
}

function mealTypeLabel(value: string | null): string {
  const labels: Record<string, string> = { breakfast: "早餐", lunch: "午餐", dinner: "晚餐", snack: "加餐" };
  return value ? labels[value] ?? "饮食" : "饮食";
}

function planError(error: unknown): string {
  return error instanceof Error ? error.message : "暂时无法读取计划，请稍后再试。";
}

const dailyPlanEncouragements = [
  "\u4e0d\u9700\u8981\u4e00\u6b21\u505a\u5230\u5b8c\u7f8e\uff0c\u5148\u5b8c\u6210\u4eca\u5929\u6700\u91cd\u8981\u7684\u4e00\u6b65\u3002",
  "\u628a\u8282\u594f\u653e\u6162\u4e00\u70b9\uff0c\u7a33\u5b9a\u5b8c\u6210\u6bd4\u5076\u5c14\u62fc\u547d\u66f4\u6709\u6548\u3002",
  "\u4eca\u5929\u7ed9\u81ea\u5df1\u7559\u4e00\u70b9\u4f59\u5730\uff0c\u505a\u5230\u4e03\u516b\u6210\u4e5f\u503c\u5f97\u80af\u5b9a\u3002",
  "\u5148\u5f00\u59cb\uff0c\u518d\u6162\u6162\u8c03\u6574\uff1b\u6bcf\u4e00\u6b21\u6267\u884c\u90fd\u4f1a\u8ba9\u8ba1\u5212\u66f4\u8d34\u5408\u4f60\u3002",
  "\u5173\u6ce8\u5f53\u4e0b\u8fd9\u4e00\u9910\u548c\u8fd9\u4e00\u7ec4\u8bad\u7ec3\uff0c\u79ef\u7d2f\u8d77\u6765\u5c31\u662f\u53d8\u5316\u3002",
  "\u5982\u679c\u4eca\u5929\u6709\u53d8\u52a8\uff0c\u4e0d\u5fc5\u91cd\u6765\uff0c\u6309\u5b9e\u9645\u60c5\u51b5\u7ee7\u7eed\u5c31\u597d\u3002",
  "\u7ed9\u81ea\u5df1\u4e00\u4e2a\u8f7b\u677e\u6536\u5c3e\uff0c\u5b8c\u6210\u4eca\u5929\u80fd\u505a\u5230\u7684\u90e8\u5206\u5c31\u5f88\u68d2\u3002",
] as const;

function dailyPlanEncouragement(dayIndex: number): string {
  return dailyPlanEncouragements[((dayIndex % dailyPlanEncouragements.length) + dailyPlanEncouragements.length) % dailyPlanEncouragements.length];
}

function localizedPlanText(value: string): string {
  const labels: Record<string, string> = {
    "Balanced meal 1": "均衡午餐 · 第 1 天",
    "Balanced meal 2": "均衡午餐 · 第 2 天",
    "Balanced meal 3": "均衡午餐 · 第 3 天",
    "Balanced meal 4": "均衡午餐 · 第 4 天",
    "Balanced meal 5": "均衡午餐 · 第 5 天",
    "Balanced meal 6": "均衡午餐 · 第 6 天",
    "Balanced meal 7": "均衡午餐 · 第 7 天",
    "Recovery day": "恢复与舒展",
    "Full-body strength": "全身力量训练",
    "Rest, stretch, and take an easy walk": "轻松散步、拉伸，并让身体充分恢复。",
    "Complete a moderate strength session": "完成一组中等强度的全身力量训练，注意动作质量与呼吸。",
    // Compatibility for plans postponed before the recovery text encoding fix.
    "????? ? ????": "\u8f7b\u6d3b\u52a8\u4e0e\u6062\u590d",
    "??????": "\u8f7b\u6d3b\u52a8\u4e0e\u6062\u590d",
    "??????????????????? 20?30 ???????????????": "\u5b89\u6392\u6b65\u884c\u3001\u8f7b\u677e\u9a91\u8f66\u6216\u745c\u4f3d 20\u201330 \u5206\u949f\u3002",
    "???????????? 20?30 ???": "\u5b89\u6392\u6b65\u884c\u3001\u8f7b\u677e\u9a91\u8f66\u6216\u745c\u4f3d 20\u201330 \u5206\u949f\u3002",
    "????": "\u6062\u590d\u4e0e\u6d3b\u52a8\u5ea6",
    "?????????????": "\u6062\u590d\u4e0b\u80a2\u548c\u80a9\u80cc\uff0c\u4fdd\u6301\u65e5\u5e38\u6d3b\u52a8\u91cf\u3002",
    "????????????????": "\u6062\u590d\u4e0b\u80a2\u548c\u80a9\u80cc\uff0c\u4fdd\u6301\u65e5\u5e38\u6d3b\u52a8\u91cf\u3002",
    "??? 5 ???????": "\u665a\u95f4\u505a\u9acb\u5c48\u808c\u548c\u80f8\u808c\u62c9\u4f38\u3002",
    "????????????": "\u665a\u95f4\u505a\u9acb\u5c48\u808c\u548c\u80f8\u808c\u62c9\u4f38\u3002",
  };
  return labels[value] ?? value;
}

function localizedPlanSplit(value: string): string {
  // Older postponed plans may contain only replacement question marks in this field.
  if (/^[?\s?.-]+$/.test(value)) return "\u6062\u590d\u4e0e\u6d3b\u52a8\u5ea6";
  return localizedPlanText(value);
}

function PlanDayDetail({ day, onPostpone, isPostponing }: { day: PlanDay; onPostpone: () => void; isPostponing: boolean }) {
  const training = day.training_instruction;
  return (
    <>
      <section className="plan-day-overview" aria-label={`${shortDate(day.date)} 计划概览`}>
        <div>
          <p>当日热量目标</p>
          <strong>{Math.round(day.calorie_target)} <small>kcal</small></strong>
        </div>
        <details className={`plan-training plan-training--${training.kind} plan-training--overview`} aria-label="训练安排">
          <summary>
            <span className="plan-training__icon" aria-hidden="true">{training.kind === "rest" ? "\u263c" : "\u2197"}</span>
            <span>
              <small>{training.kind === "rest" ? "恢复安排" : "训练安排"}</small>
              <strong>{localizedPlanText(training.title)}</strong>
              <em>{localizedPlanSplit(training.split ?? "\u6309\u4f60\u7684\u8282\u594f\u5b8c\u6210")}{training.duration_minutes ? ` · ${Math.round(training.duration_minutes)} 分钟` : ""}</em>
            </span>
            <span className="plan-training__toggle" aria-hidden="true">⌄</span>
          </summary>
          <div className="plan-training__details">
            {training.focus ? <p><b>训练重点：</b>{localizedPlanText(training.focus)}</p> : null}
            {training.warmup ? <p><b>热身：</b>{localizedPlanText(training.warmup)}</p> : null}
            <p><b>执行提示：</b>{localizedPlanText(training.instructions)}</p>
            {training.kind === "workout" && training.exercises?.length ? <div className="plan-exercise-list">{training.exercises.map((exercise) => <article key={`${exercise.name}-${exercise.sets}`}><div><strong>{exercise.name}</strong><span>{exercise.sets} × {exercise.reps} · 组间休息 {exercise.rest_seconds} 秒</span></div>{exercise.notes ? <small>{exercise.notes}</small> : null}</article>)}</div> : null}
            {training.cooldown ? <p><b>收操：</b>{localizedPlanText(training.cooldown)}</p> : null}
            {training.kind === "workout" ? <button className="plan-postpone-button" type="button" disabled={isPostponing} onClick={onPostpone}>{isPostponing ? "正在顺延…" : "今天有事？训练顺延一天"}</button> : null}
          </div>
        </details>
      </section>

      <div className="plan-meal-list" aria-label="饮食安排">
        {day.meals.map((meal, index) => (
          <details className="plan-meal" key={`${meal.name}-${index}`}>
            <summary>
              <span className="plan-meal__type">{mealTypeLabel(meal.meal_type)}</span>
              <span className="plan-meal__content"><strong>{localizedPlanText(meal.name)}</strong><small>蛋白 {Math.round(meal.protein_g)}g · 碳水 {Math.round(meal.carb_g)}g · 脂肪 {Math.round(meal.fat_g)}g</small></span>
              <strong className="plan-meal__calories">{Math.round(meal.calories)} kcal</strong>
              <span className="plan-meal__toggle" aria-hidden="true">⌄</span>
            </summary>
            <div className="plan-meal__details">
              <p className="plan-detail-label">具体食物与份量</p>
              {meal.foods?.length ? <ul>{meal.foods.map((food) => <li key={`${food.name}-${food.amount}`}><span>{food.name}</span><strong>{food.amount}</strong>{food.notes ? <small>{food.notes}</small> : null}</li>)}</ul> : <p className="plan-legacy-note">这是旧版计划，重新生成后会显示具体食物和份量。</p>}
            </div>
          </details>
        ))}
      </div>
    </>
  );
}

export function PlansPage({ onNavigate }: PlansPageProps) {
  const [plan, setPlan] = useState<FitnessPlan | null>(null);
  const [selectedDay, setSelectedDay] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isPostponing, setIsPostponing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let current = true;
    void getCurrentPlan()
      .then((result) => { if (current) { setPlan(result); setSelectedDay(todayPlanIndex(result.days)); } })
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
      setSelectedDay(todayPlanIndex(generated.days));
    } catch (nextError) {
      setError(planError(nextError));
    } finally {
      setIsGenerating(false);
    }
  }

  const day = plan?.days[selectedDay];

  async function postponeCurrentTraining() {
    if (!plan || !day || isPostponing) return;
    setIsPostponing(true);
    setError(null);
    try {
      const updated = await postponePlanDay(plan.id, day.date);
      setPlan(updated);
    } catch (nextError) {
      setError(planError(nextError));
    } finally {
      setIsPostponing(false);
    }
  }
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
              <div className="plan-header-card__eyebrow-row">
                <span className="heading-icon" aria-hidden="true">✦</span>
                <p>正在执行</p>
              </div>
              <h2>{plan.title}</h2>
              <span className="plan-header-card__date">{shortDate(plan.start_date)} — {shortDate(plan.end_date)}</span>
            </div>
            <EditorialButton variant="dingtalk-action" loading={isGenerating} loadingLabel="正在更新…" onClick={createPlan}>重新生成</EditorialButton>
          </section>
          <div className="plan-day-tabs" role="tablist" aria-label="选择计划日期">
            {plan.days.map((item, index) => <button key={item.date} type="button" role="tab" aria-selected={selectedDay === index} className={`editorial-button editorial-button--dingtalk-action plan-day-tabs__button ${selectedDay === index ? "is-active" : ""}`} onClick={() => setSelectedDay(index)}><span>第 {index + 1} 天</span><strong>{shortDate(item.date)}</strong></button>)}
          </div>
          <SectionCard title={shortDate(day.date) + " \u7684\u5b89\u6392"} subtitle={dailyPlanEncouragement(selectedDay)}>
            <PlanDayDetail day={day} onPostpone={() => void postponeCurrentTraining()} isPostponing={isPostponing} />
          </SectionCard>
          <section className="plan-ai-cta">
            <div><p>临时吃多了、没时间训练或想换食材？</p><strong>直接和 AI 说，它会帮你调整而不是让你重来。</strong></div>
            <EditorialButton variant="dingtalk-action" onClick={() => onNavigate("coach")}>和 AI 调整计划</EditorialButton>
          </section>
        </div>
      ) : null}
    </AppShell>
  );
}

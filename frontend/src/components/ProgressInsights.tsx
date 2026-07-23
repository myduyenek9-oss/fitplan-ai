import { useEffect, useMemo, useState } from "react";
import { getDailySummary, type DailySummary } from "../lib/fitplan-api";
import { listBodyMetrics, type BodyMetric } from "../lib/profile-api";
import { SectionCard } from "./SectionCard";

function localDateString(date = new Date()): string {
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 10);
}

function dateOffset(offset: number): string {
  const date = new Date();
  date.setDate(date.getDate() + offset);
  return localDateString(date);
}

const feedbackOptions = [
  ["too_hard", "太难"],
  ["dont_like", "不喜欢"],
  ["ingredients_unavailable", "食材不可得"],
  ["training_too_tiring", "训练太累"],
] as const;
type FeedbackKey = typeof feedbackOptions[number][0];

function hasRecord(summary: DailySummary): boolean {
  return summary.food_records.length > 0 || summary.exercise_records.length > 0;
}

function calculateStreak(summaries: DailySummary[]): number {
  const recordedDates = new Set(summaries.filter(hasRecord).map((summary) => summary.date));
  let streak = 0;
  for (let offset = 0; ; offset += 1) {
    if (!recordedDates.has(dateOffset(-offset))) break;
    streak += 1;
  }
  return streak;
}

export function ProgressInsights() {
  const [metrics, setMetrics] = useState<BodyMetric[]>([]);
  const [summaries, setSummaries] = useState<DailySummary[]>([]);
  const [feedback, setFeedback] = useState<FeedbackKey[]>(() => {
    try {
      return JSON.parse(localStorage.getItem("fitplan-feedback") ?? "[]") as FeedbackKey[];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    let active = true;
    async function load() {
      const nextMetrics = await listBodyMetrics().catch(() => [] as BodyMetric[]);
      const nextSummaries = await Promise.all(
        Array.from({ length: 7 }, (_, index) => getDailySummary(dateOffset(index - 6)).catch(() => null)),
      );
      if (!active) return;
      setMetrics(nextMetrics);
      setSummaries(nextSummaries.filter((item): item is DailySummary => Boolean(item)));
    }
    void load();
    return () => {
      active = false;
    };
  }, []);

  const recentMetrics = useMemo(
    () => metrics.filter((item) => item.weight_kg != null).sort((a, b) => a.logged_at.localeCompare(b.logged_at)).slice(-7),
    [metrics],
  );
  const weights = recentMetrics.map((item) => item.weight_kg as number);
  const minWeight = weights.length ? Math.min(...weights) : 0;
  const maxWeight = weights.length ? Math.max(...weights) : 1;
  const points = weights
    .map((value, index) => {
      const x = weights.length === 1 ? 50 : (index / (weights.length - 1)) * 100;
      const y = 92 - ((value - minWeight) / Math.max(maxWeight - minWeight, 0.1)) * 72;
      return `${x},${y}`;
    })
    .join(" ");

  const orderedSummaries = summaries.slice().sort((a, b) => a.date.localeCompare(b.date));
  const totalCalories = summaries.reduce((sum, item) => sum + item.food_totals.calories, 0);
  const exerciseCalories = summaries.reduce((sum, item) => sum + item.exercise_totals.calories_burned, 0);
  const recordedDays = summaries.filter(hasRecord).length;
  const trainingDays = summaries.filter((item) => item.exercise_records.length > 0).length;
  const streak = calculateStreak(summaries);

  function toggleFeedback(key: FeedbackKey) {
    const next = feedback.includes(key) ? feedback.filter((item) => item !== key) : [...feedback, key];
    setFeedback(next);
    localStorage.setItem("fitplan-feedback", JSON.stringify(next));
  }

  return (
    <section className="progress-insights" aria-label="阶段进展">
      <SectionCard title="我的进展" subtitle="用一周的趋势判断方向，不用被某一天的波动影响">
        <div className="progress-insights__grid">
          <div className="progress-chart-card">
            <div className="progress-chart-card__header">
              <strong>体重趋势</strong>
              <span>{weights.length ? `${weights[weights.length - 1].toFixed(1)} kg` : "记录体重后显示"}</span>
            </div>
            {weights.length ? (
              <svg className="progress-line-chart" viewBox="0 0 100 100" role="img" aria-label="最近体重趋势">
                <polyline points={points} fill="none" stroke="currentColor" strokeWidth="2.5" vectorEffect="non-scaling-stroke" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            ) : (
              <p className="progress-insights__empty">在“我的”里补充真实体重，就能看到变化。</p>
            )}
          </div>

          <div className="progress-chart-card">
            <div className="progress-chart-card__header">
              <strong>热量趋势</strong>
              <span>{summaries.length ? `${Math.round(totalCalories / summaries.length)} kcal/天` : "等待记录"}</span>
            </div>
            <div className="progress-bars" aria-label="每日摄入和运动消耗">
              <div className="progress-bars__legend"><span>摄入</span><span>运动</span></div>
              {orderedSummaries.map((item) => (
                <div className="progress-bars__row" key={item.date}>
                  <small>{item.date.slice(5)}</small>
                  <i style={{ width: `${Math.min(100, (item.food_totals.calories / 3000) * 100)}%` }} />
                  <b style={{ width: `${Math.min(100, (item.exercise_totals.calories_burned / 600) * 100)}%` }} />
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="progress-insights__stats">
          <div><strong>{recordedDays}</strong><span>本周记录天数</span></div>
          <div><strong>{trainingDays}</strong><span>完成训练天数</span></div>
          <div><strong>{Math.round(exerciseCalories)}</strong><span>运动消耗 kcal</span></div>
          <div><strong>{recordedDays ? Math.round(totalCalories / recordedDays) : 0}</strong><span>平均摄入 kcal</span></div>
        </div>
      </SectionCard>

      <SectionCard title={streak ? `连续记录 ${streak} 天` : "开始你的连续记录"} subtitle="每一天留下一条真实记录，就算完成">
        <div className="weekly-review">
          <strong>本周复盘</strong>
          <p>{recordedDays ? `这周共记录 ${recordedDays} 天，完成 ${trainingDays} 次训练，平均每日摄入约 ${Math.round(totalCalories / Math.max(recordedDays, 1))} kcal。` : "先记录一顿饭或一次运动，周复盘会自动开始。"}</p>
          <small>如果训练太累，优先减少一组或降低重量，不需要直接放弃。</small>
        </div>
      </SectionCard>

      <SectionCard title="告诉 AI 这周的感受" subtitle="你的反馈会影响下一次计划调整">
        <div className="feedback-options">
          {feedbackOptions.map(([key, label]) => (
            <button type="button" key={key} className={`feedback-option ${feedback.includes(key) ? "is-selected" : ""}`} onClick={() => toggleFeedback(key)} aria-pressed={feedback.includes(key)}>
              {label}
            </button>
          ))}
        </div>
      </SectionCard>
    </section>
  );
}

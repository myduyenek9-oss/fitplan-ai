import { useEffect, useState, type FormEvent } from "react";
import { AppShell } from "../components/AppShell";
import { EditorialButton } from "../components/EditorialButton";
import { SectionCard } from "../components/SectionCard";
import { getDailySummary, logExerciseFromText, logFoodFromText, undoFoodRecord, type DailySummary } from "../lib/fitplan-api";
import type { NavKey } from "../lib/types";

export type RecordsPageProps = {
  onNavigate: (key: NavKey) => void;
};

type RecordMode = "food" | "exercise";

function localDateString(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date(value));
}

function mealLabel(value: string | null): string {
  const labels: Record<string, string> = { breakfast: "早餐", lunch: "午餐", dinner: "晚餐", snack: "加餐" };
  return value ? labels[value] ?? "饮食" : "饮食";
}

function dayTitle(value: string): string {
  const today = localDateString();
  if (value === today) return "今天的记录";
  return new Intl.DateTimeFormat("zh-CN", { month: "long", day: "numeric", weekday: "long" }).format(new Date(value + "T00:00:00"));
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "暂时无法更新记录，请稍后再试。";
}

export function RecordsPage({ onNavigate }: RecordsPageProps) {
  const [date, setDate] = useState(localDateString);
  const [summary, setSummary] = useState<DailySummary | null>(null);
  const [foodText, setFoodText] = useState("");
  const [exerciseText, setExerciseText] = useState("");
  const [mode, setMode] = useState<RecordMode | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [suggestion, setSuggestion] = useState<string | null>(null);
  const [undoingId, setUndoingId] = useState<number | null>(null);

  useEffect(() => {
    let current = true;
    setError(null);
    void getDailySummary(date)
      .then((result) => { if (current) setSummary(result); })
      .catch((nextError: unknown) => { if (current) setError(errorMessage(nextError)); });
    return () => { current = false; };
  }, [date]);

  async function submit(event: FormEvent<HTMLFormElement>, nextMode: RecordMode) {
    event.preventDefault();
    const text = (nextMode === "food" ? foodText : exerciseText).trim();
    if (!text || mode) return;
    setMode(nextMode);
    setError(null);
    setSuggestion(null);
    try {
      const result = nextMode === "food" ? await logFoodFromText(text, date) : await logExerciseFromText(text, date);
      setSummary(result.daily_summary);
      setSuggestion(result.adjustment_suggestion);
      if (nextMode === "food") setFoodText("");
      else setExerciseText("");
    } catch (nextError) {
      setError(errorMessage(nextError));
    } finally {
      setMode(null);
    }
  }

  async function undoFood(id: number) {
    if (undoingId) return;
    setUndoingId(id);
    setError(null);
    try {
      await undoFoodRecord(id);
      const refreshed = await getDailySummary(date);
      setSummary(refreshed);
    } catch (nextError) {
      setError(errorMessage(nextError));
    } finally {
      setUndoingId(null);
    }
  }

  const food = summary?.food_totals;
  const exercise = summary?.exercise_totals;
  return (
    <AppShell activeNav="records" onNavigate={onNavigate} eyebrow="如实记录 · 计划自然会调整" title={dayTitle(date)} subtitle="不用因为吃多或漏练而放弃。把发生的事记下来，AI 会基于实际情况帮你继续走下去。">
      <div className="records-page">
        <section className="records-summary">
          <label>查看日期<input type="date" value={date} max={localDateString()} onChange={(event) => setDate(event.target.value)} /></label>
          <div><p>已摄入</p><strong>{Math.round(food?.calories ?? 0)} <small>kcal</small></strong></div>
          <div><p>运动消耗</p><strong>{Math.round(exercise?.calories_burned ?? 0)} <small>kcal</small></strong></div>
          <div><p>剩余热量</p><strong>{Math.round(summary?.remaining_calories ?? 0)} <small>kcal</small></strong></div>
        </section>

        {error ? <p className="dashboard-preview__error" role="alert">{error}</p> : null}
        {suggestion ? <section className="records-suggestion" role="status"><span aria-hidden="true">✦</span><div><p>AI 已更新今天的建议</p><strong>{suggestion}</strong></div><EditorialButton variant="secondary" onClick={() => onNavigate("coach")}>继续和 AI 聊</EditorialButton></section> : null}

        <div className="records-composers">
          <form className="record-composer record-composer--food" onSubmit={(event) => void submit(event, "food")}>
            <p>饮食补记</p><h2>刚刚多吃了什么？</h2><span>不用精确称重，像聊天一样描述就可以。</span>
            <label className="sr-only" htmlFor="food-record-text">补充饮食记录</label>
            <textarea id="food-record-text" rows={4} value={foodText} onChange={(event) => setFoodText(event.target.value)} placeholder="例如：下午多吃了一块蛋糕和一杯拿铁" />
            <EditorialButton type="submit" variant="accent" loading={mode === "food"} loadingLabel="正在分析…">记录饮食</EditorialButton>
          </form>
          <form className="record-composer record-composer--exercise" onSubmit={(event) => void submit(event, "exercise")}>
            <p>运动补记</p><h2>刚完成了什么运动？</h2><span>告诉 AI 时间、强度或感受，它会估算消耗。</span>
            <label className="sr-only" htmlFor="exercise-record-text">补充运动记录</label>
            <textarea id="exercise-record-text" rows={4} value={exerciseText} onChange={(event) => setExerciseText(event.target.value)} placeholder="例如：晚上快走 35 分钟，微微出汗" />
            <EditorialButton type="submit" variant="secondary" loading={mode === "exercise"} loadingLabel="正在分析…">记录运动</EditorialButton>
          </form>
        </div>

        <div className="records-list-grid">
          <SectionCard title="饮食记录" subtitle={(summary?.food_records.length ?? 0) + " 条记录"}>
            <div className="records-timeline">
              {summary?.food_records.filter((item) => item.status === "active").map((item) => <article className="records-timeline__item" key={item.id}><span aria-hidden="true">🍽</span><div><p>{mealLabel(item.meal_type)} · {formatTime(item.logged_at)}</p><h3>{item.original_text}</h3><small>蛋白 {Math.round(item.protein_g)}g · 碳水 {Math.round(item.carb_g)}g · 脂肪 {Math.round(item.fat_g)}g</small></div><aside><strong>+{Math.round(item.calories)} kcal</strong><button type="button" onClick={() => void undoFood(item.id)} disabled={undoingId === item.id}>{undoingId === item.id ? "撤销中…" : "撤销"}</button></aside></article>)}
              {summary && summary.food_records.filter((item) => item.status === "active").length === 0 ? <p className="records-timeline__empty">这一天还没有饮食记录。</p> : null}
            </div>
          </SectionCard>
          <SectionCard title="运动记录" subtitle={(summary?.exercise_records.length ?? 0) + " 次运动"}>
            <div className="records-timeline">
              {summary?.exercise_records.map((item) => <article className="records-timeline__item" key={item.id}><span className="records-timeline__icon--exercise" aria-hidden="true">↗</span><div><p>{formatTime(item.logged_at)} · {Math.round(item.duration_minutes)} 分钟</p><h3>{item.exercise_type}</h3><small>{item.description ?? "已加入今天的运动消耗。"}</small></div><aside><strong>−{Math.round(item.calories_burned)} kcal</strong></aside></article>)}
              {summary && summary.exercise_records.length === 0 ? <p className="records-timeline__empty">这一天还没有运动记录。</p> : null}
            </div>
          </SectionCard>
        </div>
      </div>
    </AppShell>
  );
}

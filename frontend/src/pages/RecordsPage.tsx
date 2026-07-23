import { useEffect, useState, type FormEvent } from "react";
import { AppShell } from "../components/AppShell";
import { EditorialButton } from "../components/EditorialButton";
import { SectionCard } from "../components/SectionCard";
import { getDailySummary, logExerciseFromText, logFoodFromText, undoExerciseRecord, undoFoodRecord, updateExerciseRecord, updateFoodRecord, type DailySummary } from "../lib/fitplan-api";
import type { NavKey } from "../lib/types";
import { formatRecordTime, getRecordDisplayTimestamp } from "../lib/record-time";

export type RecordsPageProps = { onNavigate: (key: NavKey) => void };
type RecordMode = "food" | "exercise";

const T = {
  breakfast: "\u65e9\u9910", lunch: "\u5348\u9910", dinner: "\u665a\u9910", snack: "\u52a0\u9910", food: "\u996e\u98df",
  todayRecords: "\u4eca\u5929\u7684\u8bb0\u5f55", recordsEyebrow: "\u5982\u5b9e\u8bb0\u5f55 \u00b7 \u8ba1\u5212\u81ea\u7136\u4f1a\u8c03\u6574",
  recordsSubtitle: "\u4e0d\u7528\u56e0\u4e3a\u5403\u591a\u6216\u6f0f\u7ec3\u800c\u653e\u5f03\u3002\u628a\u53d1\u751f\u7684\u4e8b\u8bb0\u4e0b\u6765\uff0cAI \u4f1a\u57fa\u4e8e\u5b9e\u9645\u60c5\u51b5\u5e2e\u4f60\u7ee7\u7eed\u8d70\u4e0b\u53bb\u3002",
  viewDate: "\u67e5\u770b\u65e5\u671f", consumed: "\u5df2\u6444\u5165", exerciseBurned: "\u8fd0\u52a8\u6d88\u8017", remaining: "\u5269\u4f59\u70ed\u91cf",
  foodEntry: "\u996e\u98df\u8865\u8bb0", foodQuestion: "\u521a\u521a\u591a\u5403\u4e86\u4ec0\u4e48\uff1f", foodHint: "\u4e0d\u7528\u7cbe\u786e\u79f0\u91cd\uff0c\u50cf\u804a\u5929\u4e00\u6837\u63cf\u8ff0\u5c31\u53ef\u4ee5\u3002", foodLabel: "\u8865\u5145\u996e\u98df\u8bb0\u5f55", foodPlaceholder: "\u4f8b\u5982\uff1a\u4e0b\u5348\u591a\u5403\u4e86\u4e00\u5757\u86cb\u7cd5\u548c\u4e00\u676f\u62ff\u94c1", recordFood: "\u8bb0\u5f55\u996e\u98df",
  exerciseEntry: "\u8fd0\u52a8\u8865\u8bb0", exerciseQuestion: "\u4eca\u5929\u505a\u4e86\u4ec0\u4e48\u8fd0\u52a8\uff1f", exerciseHint: "\u544a\u8bc9 AI \u65f6\u95f4\u3001\u5f3a\u5ea6\u6216\u611f\u53d7\uff0c\u5b83\u4f1a\u4f30\u7b97\u6d88\u8017\u3002", exerciseLabel: "\u8865\u5145\u8fd0\u52a8\u8bb0\u5f55", exercisePlaceholder: "\u4f8b\u5982\uff1a\u665a\u4e0a\u5feb\u8d70 35 \u5206\u949f\uff0c\u5fae\u5fae\u51fa\u6c57", recordExercise: "\u8bb0\u5f55\u8fd0\u52a8",
  foodRecords: "\u996e\u98df\u8bb0\u5f55", exerciseRecords: "\u8fd0\u52a8\u8bb0\u5f55", noFood: "\u8fd9\u4e00\u5929\u8fd8\u6ca1\u6709\u996e\u98df\u8bb0\u5f55\u3002", noExercise: "\u8fd9\u4e00\u5929\u8fd8\u6ca1\u6709\u8fd0\u52a8\u8bb0\u5f55\u3002",
  protein: "\u86cb\u767d\u8d28", carbs: "\u78b3\u6c34", fat: "\u8102\u80aa", estimated: "\u4f30\u7b97\u533a\u95f4\uff1a", minutes: "\u5206\u949f", noDescription: "\u672a\u586b\u5199\u8be6\u7ec6\u8bf4\u660e", undo: "\u64a4\u9500", undoing: "\u64a4\u9500\u4e2d\u2026", correctCalories: "\u4fee\u6b63\u70ed\u91cf", correctedCalories: "\u4fee\u6b63\u540e\u7684\u70ed\u91cf", save: "\u4fdd\u5b58", saving: "\u4fdd\u5b58\u4e2d\u2026",
  correctedNotice: "\u70ed\u91cf\u5df2\u4fee\u6b63\uff0c\u4eca\u65e5\u6c47\u603b\u5df2\u91cd\u65b0\u8ba1\u7b97\u3002",
  foodUndoNotice: "\u5df2\u64a4\u9500\u8fd9\u6761\u996e\u98df\u8bb0\u5f55\uff0c\u4eca\u65e5\u6444\u5165\u548c\u5269\u4f59\u70ed\u91cf\u5df2\u91cd\u65b0\u8ba1\u7b97\u3002",
  exerciseUndoNotice: "\u5df2\u64a4\u9500\u8fd9\u6761\u8fd0\u52a8\u8bb0\u5f55\uff0c\u4eca\u65e5\u8fd0\u52a8\u6d88\u8017\u548c\u5269\u4f59\u70ed\u91cf\u5df2\u91cd\u65b0\u8ba1\u7b97\u3002",
  error: "\u6682\u65f6\u65e0\u6cd5\u66f4\u65b0\u8bb0\u5f55\uff0c\u8bf7\u7a0d\u540e\u518d\u8bd5\u3002",
} as const;

function localDateString(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}
function mealLabel(value: string | null): string { const labels: Record<string, string> = { breakfast: T.breakfast, lunch: T.lunch, dinner: T.dinner, snack: T.snack }; return value ? labels[value] ?? T.food : T.food; }
function dayTitle(value: string): string { return value === localDateString() ? T.todayRecords : new Intl.DateTimeFormat("zh-CN", { month: "long", day: "numeric", weekday: "long" }).format(new Date(value + "T00:00:00")); }
function errorMessage(error: unknown): string { return error instanceof Error ? error.message : T.error; }

export function RecordsPage({ onNavigate }: RecordsPageProps) {
  const [date, setDate] = useState(localDateString);
  const [summary, setSummary] = useState<DailySummary | null>(null);
  const [foodText, setFoodText] = useState(""); const [exerciseText, setExerciseText] = useState("");
  const [mode, setMode] = useState<RecordMode | null>(null); const [error, setError] = useState<string | null>(null);
  const [suggestion, setSuggestion] = useState<string | null>(null); const [notice, setNotice] = useState<string | null>(null);
  const [undoingFoodId, setUndoingFoodId] = useState<number | null>(null); const [undoingExerciseId, setUndoingExerciseId] = useState<number | null>(null);
  const [correctionValues, setCorrectionValues] = useState<Record<string, string>>({}); const [savingCorrectionId, setSavingCorrectionId] = useState<string | null>(null);

  useEffect(() => { let current = true; setError(null); void getDailySummary(date).then((result) => { if (current) setSummary(result); }).catch((nextError: unknown) => { if (current) setError(errorMessage(nextError)); }); return () => { current = false; }; }, [date]);
  async function submit(event: FormEvent<HTMLFormElement>, nextMode: RecordMode) {
    event.preventDefault(); const text = (nextMode === "food" ? foodText : exerciseText).trim(); if (!text || mode) return;
    setMode(nextMode); setError(null); setSuggestion(null); setNotice(null);
    try { const result = nextMode === "food" ? await logFoodFromText(text, date) : await logExerciseFromText(text, date); setSummary(result.daily_summary); setSuggestion(result.adjustment_suggestion); if (nextMode === "food") setFoodText(""); else setExerciseText(""); }
    catch (nextError) { setError(errorMessage(nextError)); } finally { setMode(null); }
  }
  async function undoFood(id: number) { if (undoingFoodId !== null) return; setUndoingFoodId(id); setError(null); setNotice(null); try { await undoFoodRecord(id); setSummary(await getDailySummary(date)); setNotice(T.foodUndoNotice); } catch (nextError) { setError(errorMessage(nextError)); } finally { setUndoingFoodId(null); } }
  async function undoExercise(id: number) { if (undoingExerciseId !== null) return; setUndoingExerciseId(id); setError(null); setNotice(null); try { await undoExerciseRecord(id); setSummary(await getDailySummary(date)); setNotice(T.exerciseUndoNotice); } catch (nextError) { setError(errorMessage(nextError)); } finally { setUndoingExerciseId(null); } }
  async function saveCorrection(kind: RecordMode, id: number) {
    const key = `${kind}-${id}`; const value = Number(correctionValues[key]); if (!Number.isFinite(value) || value <= 0) return;
    setSavingCorrectionId(key); setError(null); setNotice(null);
    try { if (kind === "food") await updateFoodRecord(id, { calories: value }); else await updateExerciseRecord(id, { calories_burned: value }); setSummary(await getDailySummary(date)); setNotice(T.correctedNotice); }
    catch (nextError) { setError(errorMessage(nextError)); } finally { setSavingCorrectionId(null); }
  }

  const food = summary?.food_totals; const exercise = summary?.exercise_totals;
  const foods = (summary?.food_records ?? []).filter((item) => item.status === "active").sort((left, right) => getRecordDisplayTimestamp({ loggedAt: left.logged_at, createdAt: left.created_at, sourceText: left.original_text, preferCreatedAtForRoundedAiTime: left.parsed_content.source === "ai" }) - getRecordDisplayTimestamp({ loggedAt: right.logged_at, createdAt: right.created_at, sourceText: right.original_text, preferCreatedAtForRoundedAiTime: right.parsed_content.source === "ai" }));
  const exercises = (summary?.exercise_records ?? []).slice().sort((left, right) => getRecordDisplayTimestamp({ loggedAt: left.logged_at }) - getRecordDisplayTimestamp({ loggedAt: right.logged_at }));

  return <AppShell activeNav="records" onNavigate={onNavigate} eyebrow={T.recordsEyebrow} title={dayTitle(date)} subtitle={T.recordsSubtitle}>
    <div className="records-page">
      <section className="records-summary"><label>{T.viewDate}<input type="date" value={date} max={localDateString()} onChange={(event) => setDate(event.target.value)} /></label><div><p>{T.consumed}</p><strong>{Math.round(food?.calories ?? 0)} <small>kcal</small></strong></div><div><p>{T.exerciseBurned}</p><strong>{Math.round(exercise?.calories_burned ?? 0)} <small>kcal</small></strong></div><div><p>{T.remaining}</p><strong>{Math.round(summary?.remaining_calories ?? 0)} <small>kcal</small></strong></div></section>
      {error ? <p className="dashboard-preview__error" role="alert">{error}</p> : null}
      {notice ? <p className="records-notice" role="status"><span aria-hidden="true">{"\u2713"}</span>{notice}</p> : null}
      {suggestion ? <section className="records-suggestion" role="status"><span aria-hidden="true">{"\u2726"}</span><div><p>AI {"\u5df2\u66f4\u65b0\u4eca\u5929\u7684\u5efa\u8bae"}</p><strong>{suggestion}</strong></div><EditorialButton variant="secondary" onClick={() => onNavigate("coach")}>{"\u7ee7\u7eed\u548c AI \u804a"}</EditorialButton></section> : null}
      <div className="records-composers">
        <form className="record-composer record-composer--food" onSubmit={(event) => void submit(event, "food")}><p>{T.foodEntry}</p><h2>{T.foodQuestion}</h2><span>{T.foodHint}</span><label className="sr-only" htmlFor="food-record-text">{T.foodLabel}</label><textarea id="food-record-text" rows={4} value={foodText} onChange={(event) => setFoodText(event.target.value)} placeholder={T.foodPlaceholder} /><EditorialButton type="submit" variant="dingtalk-action" loading={mode === "food"} loadingLabel={"\u6b63\u5728\u5206\u6790\u2026"}>{T.recordFood}</EditorialButton></form>
        <form className="record-composer record-composer--exercise" onSubmit={(event) => void submit(event, "exercise")}><p>{T.exerciseEntry}</p><h2>{T.exerciseQuestion}</h2><span>{T.exerciseHint}</span><label className="sr-only" htmlFor="exercise-record-text">{T.exerciseLabel}</label><textarea id="exercise-record-text" rows={4} value={exerciseText} onChange={(event) => setExerciseText(event.target.value)} placeholder={T.exercisePlaceholder} /><EditorialButton type="submit" variant="dingtalk-action" loading={mode === "exercise"} loadingLabel={"\u6b63\u5728\u5206\u6790\u2026"}>{T.recordExercise}</EditorialButton></form>
      </div>
      <div className="records-list-grid">
        <SectionCard title={T.foodRecords} subtitle={`${summary?.food_records.length ?? 0} ${"\u6761\u8bb0\u5f55"}`}><div className="records-timeline">{foods.map((item) => { const key = `food-${item.id}`; return <article className="records-timeline__item" key={item.id}><span aria-hidden="true">{"\ud83c\udf7d\ufe0f"}</span><div><p>{mealLabel(item.meal_type)} {"\u00b7"} {formatRecordTime({ loggedAt: item.logged_at, createdAt: item.created_at, sourceText: item.original_text, preferCreatedAtForRoundedAiTime: item.parsed_content.source === "ai" })}</p><h3>{item.original_text}</h3><small>{T.protein} {Math.round(item.protein_g)}g {"\u00b7"} {T.carbs} {Math.round(item.carb_g)}g {"\u00b7"} {T.fat} {Math.round(item.fat_g)}g</small><small className="estimate-range">{T.estimated}{Math.round(item.calories_min ?? item.calories * 0.8)}{"\u2013"}{Math.round(item.calories_max ?? item.calories * 1.2)} kcal</small></div><aside><strong>+{Math.round(item.calories)} kcal</strong><button type="button" onClick={() => void undoFood(item.id)} disabled={undoingFoodId === item.id}>{undoingFoodId === item.id ? T.undoing : T.undo}</button><details className="record-correction"><summary>{T.correctCalories}</summary><input aria-label={T.correctedCalories} type="number" min="1" value={correctionValues[key] ?? Math.round(item.calories)} onChange={(event) => setCorrectionValues((current) => ({ ...current, [key]: event.target.value }))} /><button type="button" onClick={() => void saveCorrection("food", item.id)} disabled={savingCorrectionId === key}>{savingCorrectionId === key ? T.saving : T.save}</button></details></aside></article>; })}{summary && foods.length === 0 ? <p className="records-timeline__empty">{T.noFood}</p> : null}</div></SectionCard>
        <SectionCard title={T.exerciseRecords} subtitle={`${summary?.exercise_records.length ?? 0} ${"\u6b21\u8fd0\u52a8"}`}><div className="records-timeline">{exercises.map((item) => { const key = `exercise-${item.id}`; return <article className="records-timeline__item" key={item.id}><span className="records-timeline__icon--exercise" aria-hidden="true">{"\ud83c\udfc3"}</span><div><p>{formatRecordTime({ loggedAt: item.logged_at })} {"\u00b7"} {Math.round(item.duration_minutes)} {T.minutes}</p><h3>{item.exercise_type}</h3><small>{item.description ?? T.noDescription}</small><small className="estimate-range">{T.estimated}{Math.round(item.calories_burned_min ?? item.calories_burned * 0.8)}{"\u2013"}{Math.round(item.calories_burned_max ?? item.calories_burned * 1.2)} kcal</small></div><aside><strong>{"\u2212"}{Math.round(item.calories_burned)} kcal</strong><button type="button" onClick={() => void undoExercise(item.id)} disabled={undoingExerciseId === item.id}>{undoingExerciseId === item.id ? T.undoing : T.undo}</button><details className="record-correction"><summary>{T.correctCalories}</summary><input aria-label={T.correctedCalories} type="number" min="1" value={correctionValues[key] ?? Math.round(item.calories_burned)} onChange={(event) => setCorrectionValues((current) => ({ ...current, [key]: event.target.value }))} /><button type="button" onClick={() => void saveCorrection("exercise", item.id)} disabled={savingCorrectionId === key}>{savingCorrectionId === key ? T.saving : T.save}</button></details></aside></article>; })}{summary && exercises.length === 0 ? <p className="records-timeline__empty">{T.noExercise}</p> : null}</div></SectionCard>
      </div>
    </div>
  </AppShell>;
}

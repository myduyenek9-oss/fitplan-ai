import { useState } from "react";
import { EditorialButton } from "../../components/EditorialButton";
import { logFoodFromText, type ExerciseRecord, type NaturalLanguageFoodResult } from "../../lib/fitplan-api";

export type QuickRecordComposerProps = {
  date: string;
  onRecorded?: (result: NaturalLanguageFoodResult) => void;
};

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "暂时无法解析这条记录，请稍后再试。";
}

function isExerciseRecord(record: NaturalLanguageFoodResult["record"]): record is ExerciseRecord {
  return "calories_burned" in record;
}

function foodCalories(result: NaturalLanguageFoodResult): number | null {
  if (result.recorded_food) return result.recorded_food.calories;
  return isExerciseRecord(result.record) ? null : result.record.calories;
}

export function QuickRecordComposer({ date, onRecorded }: QuickRecordComposerProps) {
  const [text, setText] = useState("");
  const [result, setResult] = useState<NaturalLanguageFoodResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submit() {
    const normalizedText = text.trim();
    if (!normalizedText || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      const nextResult = await logFoodFromText(normalizedText, date);
      setResult(nextResult);
      setText("");
      onRecorded?.(nextResult);
    } catch (nextError) {
      setError(errorMessage(nextError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="quick-record-composer" aria-labelledby="quick-record-title">
      <div className="quick-record-composer__header">
        <div>
          <p className="quick-record-composer__eyebrow">随手补记</p>
          <h2 id="quick-record-title">吃了什么、练了什么，直接告诉我</h2>
        </div>
        <span className="quick-record-composer__spark" aria-hidden="true">✦</span>
      </div>

      <label className="quick-record-composer__label" htmlFor="quick-food-record">
        补充饮食或运动记录
      </label>
      <textarea
        id="quick-food-record"
        className="quick-record-composer__input"
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="例如：刚吃了两串烧烤，又慢跑了10分钟"
        rows={3}
      />
      <div className="quick-record-composer__actions">
        <EditorialButton loading={isSubmitting} loadingLabel="正在分析…" onClick={submit} variant="dingtalk-action">
          记录并调整
        </EditorialButton>
        <p>AI 会自动拆分饮食和运动，并同步今日汇总。</p>
      </div>

      {error ? (
        <p className="quick-record-composer__error" role="alert">
          {error}
        </p>
      ) : null}

      {result ? (
        <div className="quick-record-composer__result" role="status">
          {foodCalories(result) !== null ? (
            <p>已记录饮食约 {Math.round(foodCalories(result) ?? 0)} kcal</p>
          ) : null}
          {result.recorded_exercise ? (
            <p>已记录运动约 {Math.round(result.recorded_exercise.calories_burned)} kcal</p>
          ) : isExerciseRecord(result.record) ? (
            <p>已记录运动约 {Math.round(result.record.calories_burned)} kcal</p>
          ) : null}
          <p>{result.adjustment_suggestion}</p>
        </div>
      ) : null}
    </section>
  );
}

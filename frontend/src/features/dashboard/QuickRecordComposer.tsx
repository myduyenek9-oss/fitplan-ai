import { useState } from "react";
import { EditorialButton } from "../../components/EditorialButton";
import { logFoodFromText, type NaturalLanguageFoodResult } from "../../lib/fitplan-api";

export type QuickRecordComposerProps = {
  date: string;
  onRecorded?: (result: NaturalLanguageFoodResult) => void;
};

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "暂时无法解析这条记录，请稍后再试。";
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
          <h2 id="quick-record-title">多吃了什么，直接告诉我</h2>
        </div>
        <span className="quick-record-composer__spark" aria-hidden="true">✦</span>
      </div>

      <label className="quick-record-composer__label" htmlFor="quick-food-record">
        补充饮食记录
      </label>
      <textarea
        id="quick-food-record"
        className="quick-record-composer__input"
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="例如：下午多吃了一块蛋糕，或者喝了一杯奶茶"
        rows={3}
      />
      <div className="quick-record-composer__actions">
        <EditorialButton loading={isSubmitting} loadingLabel="正在分析…" onClick={submit} variant="accent">
          记录并调整
        </EditorialButton>
        <p>AI 会把热量补进今天的总量，并给你下一餐建议。</p>
      </div>

      {error ? (
        <p className="quick-record-composer__error" role="alert">
          {error}
        </p>
      ) : null}

      {result ? (
        <div className="quick-record-composer__result" role="status">
          <p>已记录约 {Math.round(result.record.calories)} kcal</p>
          <p>{result.adjustment_suggestion}</p>
        </div>
      ) : null}
    </section>
  );
}

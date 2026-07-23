import { useEffect, useMemo, useState, type FormEvent } from "react";
import { EditorialButton } from "../components/EditorialButton";
import { DingTalkNotificationSettings } from "../components/DingTalkNotificationSettings";
import {
  type ActivityLevel,
  type CalorieSex,
  type CalorieTargets,
  type GoalType,
  createBodyMetric,
  getActiveGoal,
  getProfile,
  listBodyMetrics,
  previewCalorieTargets,
  upsertGoal,
  upsertProfile,
} from "../lib/profile-api";

export type InitialSetupPageProps = {
  onCompleted: () => void;
  isEditing?: boolean;
  onLogout?: () => void;
  embedded?: boolean;
};

const activityOptions: Array<{ value: ActivityLevel; label: string; detail: string }> = [
  { value: "sedentary", label: "久坐", detail: "日常活动很少" },
  { value: "light", label: "轻度活动", detail: "每周运动 1–3 次" },
  { value: "moderate", label: "中等活动", detail: "每周运动 3–5 次" },
  { value: "active", label: "高活动", detail: "每周训练 6–7 次" },
  { value: "very_active", label: "很高活动", detail: "高强度训练或体力工作" },
];

const goalOptions: Array<{ value: GoalType; label: string; detail: string }> = [
  { value: "fat_loss", label: "减脂", detail: "以温和热量缺口，优先保留肌肉" },
  { value: "maintenance", label: "维持", detail: "保持体重与更稳定的生活节奏" },
  { value: "muscle_gain", label: "增肌", detail: "提供训练恢复所需的额外能量" },
];

function localDate(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset();
  return new Date(now.getTime() - offset * 60_000).toISOString().slice(0, 10);
}

function getAge(birthDate: string): number | null {
  if (!birthDate) return null;
  const birth = new Date(birthDate + "T00:00:00");
  if (Number.isNaN(birth.valueOf())) return null;
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  if (today.getMonth() < birth.getMonth() || (today.getMonth() === birth.getMonth() && today.getDate() < birth.getDate())) age -= 1;
  return age;
}

function readError(error: unknown): string {
  return error instanceof Error ? error.message : "暂时无法保存资料，请稍后重试。";
}

function usableSex(value: string | null): CalorieSex {
  return value === "male" || value === "female" ? value : "female";
}

export function InitialSetupPage({ onCompleted, isEditing = false, onLogout, embedded = false }: InitialSetupPageProps) {
  const [displayName, setDisplayName] = useState("");
  const [sex, setSex] = useState<CalorieSex>("female");
  const [birthDate, setBirthDate] = useState("");
  const [heightCm, setHeightCm] = useState("");
  const [weightKg, setWeightKg] = useState("");
  const [activityLevel, setActivityLevel] = useState<ActivityLevel>("moderate");
  const [goal, setGoal] = useState<GoalType>("fat_loss");
  const [targetWeightKg, setTargetWeightKg] = useState("");
  const [targetDate, setTargetDate] = useState("");
  const [targets, setTargets] = useState<CalorieTargets | null>(null);
  const [savedWeightKg, setSavedWeightKg] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(isEditing);
  const [isCalculating, setIsCalculating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const age = useMemo(() => getAge(birthDate), [birthDate]);

  useEffect(() => {
    if (!isEditing) return;
    let active = true;
    setIsLoading(true);
    setError(null);

    void Promise.all([getProfile(), getActiveGoal(), listBodyMetrics()])
      .then(([profile, activeGoal, metrics]) => {
        if (!active) return;
        setDisplayName(profile.display_name ?? "");
        setSex(usableSex(profile.sex));
        setBirthDate(profile.birth_date ?? "");
        setHeightCm(profile.height_cm == null ? "" : String(profile.height_cm));
        setActivityLevel(activeGoal.activity_level);
        setGoal(activeGoal.goal_type);
        setTargetWeightKg(activeGoal.target_weight_kg == null ? "" : String(activeGoal.target_weight_kg));
        setTargetDate(activeGoal.target_date ?? "");
        setTargets({
          bmr: 0,
          tdee: 0,
          daily_calories: activeGoal.daily_calories,
          protein_g: activeGoal.protein_g,
          carb_g: activeGoal.carb_g,
          fat_g: activeGoal.fat_g,
        });
        const latestWeight = metrics[0]?.weight_kg ?? null;
        setSavedWeightKg(latestWeight);
        setWeightKg(latestWeight == null ? "" : String(latestWeight));
      })
      .catch((nextError: unknown) => {
        if (active) setError("读取已保存资料失败：" + readError(nextError));
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });

    return () => { active = false; };
  }, [isEditing]);

  function getInput() {
    const height = Number(heightCm);
    const weight = Number(weightKg);
    if (!age || age < 18 || age > 100) throw new Error("请填写有效的出生日期（18–100 岁）。");
    if (!Number.isFinite(height) || height < 100 || height > 230) throw new Error("身高请填写 100–230 cm 之间的数值。");
    if (!Number.isFinite(weight) || weight < 30 || weight > 250) throw new Error("体重请填写 30–250 kg 之间的数值。");
    return { age, height, weight };
  }

  async function calculate() {
    try {
      const input = getInput();
      setIsCalculating(true);
      setError(null);
      const nextTargets = await previewCalorieTargets({ age: input.age, sex, weight_kg: input.weight, height_cm: input.height, activity_level: activityLevel, goal });
      setTargets(nextTargets);
      return nextTargets;
    } catch (nextError) {
      setError(readError(nextError));
      return null;
    } finally {
      setIsCalculating(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSaving || isLoading) return;
    let input: { age: number; height: number; weight: number };
    try {
      input = getInput();
    } catch (nextError) {
      setError(readError(nextError));
      return;
    }

    setIsSaving(true);
    setError(null);
    try {
      const currentTargets = await previewCalorieTargets({ age: input.age, sex, weight_kg: input.weight, height_cm: input.height, activity_level: activityLevel, goal });
      setTargets(currentTargets);
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Shanghai";
      await upsertProfile({ display_name: displayName.trim() || null, sex, birth_date: birthDate, height_cm: input.height, timezone });
      await upsertGoal({
        goal_type: goal,
        daily_calories: currentTargets.daily_calories,
        protein_g: currentTargets.protein_g,
        carb_g: currentTargets.carb_g,
        fat_g: currentTargets.fat_g,
        activity_level: activityLevel,
        target_weight_kg: targetWeightKg ? Number(targetWeightKg) : null,
        target_date: targetDate || null,
      });
      if (savedWeightKg === null || savedWeightKg !== input.weight) {
        await createBodyMetric({ weight_kg: input.weight, logged_at: new Date().toISOString() });
        setSavedWeightKg(input.weight);
      }
      onCompleted();
    } catch (nextError) {
      setError(readError(nextError));
    } finally {
      setIsSaving(false);
    }
  }

  const isDisabled = isLoading || isSaving;
  const eyebrow = "第一次，先认识你";
  const title = <>把目标变成<br />每天做得到的事。</>;

  const Root = embedded ? "div" : "main";

  return <Root className={isEditing ? "initial-setup-page initial-setup-page--editing" : "initial-setup-page"}>
    {!isEditing ? <section className="initial-setup-page__intro">
      <p className="initial-setup-page__brand">FitPlan AI<span>·</span></p>
      <div><p className="initial-setup-page__eyebrow">{eyebrow}</p><h1>{title}</h1><p>填写基础资料后，我们会计算适合你的每日热量和三大营养素目标。之后你吃多了、练少了，都可以随时让 AI 帮你重新调整。</p></div>
      <div className="initial-setup-page__tip"><span aria-hidden="true">✦</span><p>建议使用真实、近期的体重数据。目标不是绝对限制，而是让你看见可以持续的方向。</p></div>
    </section> : <div className="initial-setup-page__editing-note">
      <h1 className="initial-setup-page__editing-title">让计划继续<br />贴合现在的你。</h1>
      <div className="initial-setup-page__tip"><span aria-hidden="true">✦</span><p>建议使用真实、近期的体重数据。目标不是绝对限制，而是让你看见可以持续的方向。</p></div>
    </div>}
    <section className="initial-setup-page__form-wrap" aria-label="设置健康资料与目标">
      {isLoading ? <div className="initial-setup-form__loading" role="status">正在读取已保存的资料…</div> : <form className="initial-setup-form" onSubmit={submit} noValidate>
        <header><p>{isEditing ? "我的资料 / 调整计划" : "01 / 建立基础"}</p><h2>{isEditing ? "更新健康目标" : "你的健康目标"}</h2><span>所有数据仅用于计算你的个人计划。</span></header>
        <div className="initial-setup-form__grid">
          <label className="initial-setup-form__field initial-setup-form__field--full" htmlFor="profile-name"><span>怎么称呼你 <em>（可选）</em></span><input id="profile-name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="例如：小满" disabled={isDisabled} /></label>
          <label className="initial-setup-form__field" htmlFor="profile-sex"><span>生理性别</span><select id="profile-sex" value={sex} onChange={(event) => setSex(event.target.value as CalorieSex)} disabled={isDisabled}><option value="female">女性</option><option value="male">男性</option></select></label>
          <label className="initial-setup-form__field" htmlFor="profile-birthdate"><span>出生日期</span><input id="profile-birthdate" type="date" max={localDate()} value={birthDate} onChange={(event) => setBirthDate(event.target.value)} disabled={isDisabled} /></label>
          <label className="initial-setup-form__field" htmlFor="profile-height"><span>身高（cm）</span><input id="profile-height" inputMode="decimal" value={heightCm} onChange={(event) => setHeightCm(event.target.value)} placeholder="例如：165" disabled={isDisabled} /></label>
          <label className="initial-setup-form__field" htmlFor="profile-weight"><span>当前体重（kg）</span><input id="profile-weight" inputMode="decimal" value={weightKg} onChange={(event) => setWeightKg(event.target.value)} placeholder="例如：58.5" disabled={isDisabled} /></label>
        </div>
        <fieldset className="initial-setup-form__choices"><legend>你的主要目标</legend><div>{goalOptions.map((option) => <label className={goal === option.value ? "initial-setup-form__choice is-selected" : "initial-setup-form__choice"} key={option.value}><input type="radio" name="goal" value={option.value} checked={goal === option.value} onChange={() => setGoal(option.value)} disabled={isDisabled} /><strong>{option.label}</strong><span>{option.detail}</span></label>)}</div></fieldset>
        <label className="initial-setup-form__field" htmlFor="profile-activity"><span>日常活动水平</span><select id="profile-activity" value={activityLevel} onChange={(event) => setActivityLevel(event.target.value as ActivityLevel)} disabled={isDisabled}>{activityOptions.map((option) => <option key={option.value} value={option.value}>{option.label} · {option.detail}</option>)}</select></label>
        <div className="initial-setup-form__grid">
          <label className="initial-setup-form__field" htmlFor="profile-target-weight"><span>目标体重（kg）<em>（可选）</em></span><input id="profile-target-weight" inputMode="decimal" value={targetWeightKg} onChange={(event) => setTargetWeightKg(event.target.value)} placeholder="例如：55" disabled={isDisabled} /></label>
          <label className="initial-setup-form__field" htmlFor="profile-target-date"><span>希望完成时间 <em>（可选）</em></span><input id="profile-target-date" type="date" min={localDate()} value={targetDate} onChange={(event) => setTargetDate(event.target.value)} disabled={isDisabled} /></label>
        </div>
        <div className="initial-setup-form__calculation"><div><p>今日建议目标</p>{targets ? <div className="initial-setup-form__targets" role="status"><strong>{targets.daily_calories}<small> kcal</small></strong><span>蛋白 {targets.protein_g}g · 碳水 {targets.carb_g}g · 脂肪 {targets.fat_g}g</span></div> : <span>填写资料后，先计算一版适合你的热量和营养素目标。</span>}</div><EditorialButton type="button" variant="secondary" loading={isCalculating} loadingLabel="计算中…" onClick={calculate} disabled={isDisabled}>计算目标</EditorialButton></div>
        {error ? <p className="initial-setup-form__error" role="alert">{error}</p> : null}
        <EditorialButton className="initial-setup-form__submit" type="submit" variant="accent" loading={isSaving} loadingLabel="正在保存…">{isEditing ? "保存修改" : "保存目标，进入今日计划"}</EditorialButton>{isEditing && onLogout ? <EditorialButton className="initial-setup-form__logout" type="button" variant="secondary" onClick={onLogout} disabled={isDisabled}>退出登录 / 切换账号</EditorialButton> : null}
      </form>}
      {isEditing && !isLoading ? <DingTalkNotificationSettings /> : null}
    </section>
  </Root>;
}

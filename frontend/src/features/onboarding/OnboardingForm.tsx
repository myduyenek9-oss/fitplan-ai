import { useState, type FormEvent } from "react";
import { EditorialButton } from "../../components/EditorialButton";
import { login, setupAccount } from "../../lib/auth-api";
import { ApiError, setAccessToken } from "../../lib/api";

type AuthMode = "setup" | "login";

export type OnboardingFormProps = {
  onAuthenticated: () => void;
};

function readError(error: unknown): string {
  if (error instanceof ApiError && error.status === 401) {
    return "用户名或密码不正确，请重新输入。";
  }
  return error instanceof Error ? error.message : "暂时无法完成操作，请稍后重试。";
}

export function OnboardingForm({ onAuthenticated }: OnboardingFormProps) {
  const [mode, setMode] = useState<AuthMode>("setup");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isSetup = mode === "setup";
  const title = isSetup ? "先创建你的健康档案" : "欢迎回来，继续今天的节奏";
  const submitLabel = isSetup ? "创建并开始" : "登录 FitPlan AI";

  function switchMode(nextMode: AuthMode) {
    setMode(nextMode);
    setError(null);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const credentials = { username: username.trim(), password };
    if (!credentials.username) { setError("请填写一个用户名。"); return; }
    if (isSetup && credentials.password.length < 8) { setError("为了账号安全，密码至少需要 8 位。"); return; }
    if (!credentials.password) { setError("请填写密码。"); return; }

    setIsSubmitting(true);
    setError(null);
    try {
      if (isSetup) await setupAccount(credentials);
      const token = await login(credentials);
      setAccessToken(token.access_token);
      onAuthenticated();
    } catch (nextError) {
      if (isSetup && nextError instanceof ApiError && nextError.status === 409) {
        setMode("login");
        setError("这个 FitPlan 已经创建过账号了，请直接登录。");
      } else {
        setError(readError(nextError));
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="onboarding-form">
      <div className="onboarding-form__mode" aria-label="账号操作">
        <button className={isSetup ? "onboarding-form__mode-button is-active" : "onboarding-form__mode-button"} type="button" aria-pressed={isSetup} onClick={() => switchMode("setup")}>首次使用</button>
        <button className={!isSetup ? "onboarding-form__mode-button is-active" : "onboarding-form__mode-button"} type="button" aria-pressed={!isSetup} onClick={() => switchMode("login")}>已有账号</button>
      </div>
      <div className="onboarding-form__heading">
        <p className="onboarding-form__eyebrow">你的私有健康空间</p>
        <h1>{title}</h1>
        <p>{isSetup ? "仅需一个账号，就可以保存饮食、训练、计划和每次与 AI 的调整。" : "登录后即可继续记录热量，并让 AI 根据今天的变化调整下一餐。"}</p>
      </div>
      <form onSubmit={submit} noValidate>
        <label className="onboarding-form__field" htmlFor="auth-username"><span>用户名</span><input id="auth-username" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} placeholder="例如：momo" disabled={isSubmitting} /></label>
        <label className="onboarding-form__field" htmlFor="auth-password"><span>密码</span><input id="auth-password" type="password" autoComplete={isSetup ? "new-password" : "current-password"} value={password} onChange={(event) => setPassword(event.target.value)} placeholder={isSetup ? "至少 8 位" : "输入你的密码"} disabled={isSubmitting} /></label>
        {error ? <p className="onboarding-form__error" role="alert">{error}</p> : null}
        <EditorialButton className="onboarding-form__submit" type="submit" variant="accent" loading={isSubmitting} loadingLabel="正在进入…">{submitLabel}</EditorialButton>
      </form>
      <p className="onboarding-form__privacy">账号信息只用于保护你的个人健康记录，不会展示给其他人。</p>
    </div>
  );
}

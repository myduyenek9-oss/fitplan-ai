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
    return "????????????????";
  }

  return error instanceof Error ? error.message : "???????????????";
}

export function OnboardingForm({ onAuthenticated }: OnboardingFormProps) {
  const [mode, setMode] = useState<AuthMode>("setup");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isSetup = mode === "setup";
  const title = isSetup ? "?????????" : "????????????";
  const submitLabel = isSetup ? "?????" : "?? FitPlan AI";

  function switchMode(nextMode: AuthMode) {
    setMode(nextMode);
    setError(null);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const credentials = { username: username.trim(), password };

    if (!credentials.username) {
      setError("?????????");
      return;
    }

    if (isSetup && credentials.password.length < 8) {
      setError("????????????? 8 ??");
      return;
    }

    if (!credentials.password) {
      setError("??????");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      if (isSetup) {
        await setupAccount(credentials);
      }

      const token = await login(credentials);
      setAccessToken(token.access_token);
      onAuthenticated();
    } catch (nextError) {
      if (isSetup && nextError instanceof ApiError && nextError.status === 409) {
        setMode("login");
        setError("?? FitPlan ???????????????");
      } else {
        setError(readError(nextError));
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="onboarding-form">
      <div className="onboarding-form__mode" aria-label="????">
        <button
          className={isSetup ? "onboarding-form__mode-button is-active" : "onboarding-form__mode-button"}
          type="button"
          aria-pressed={isSetup}
          onClick={() => switchMode("setup")}
        >
          ????
        </button>
        <button
          className={!isSetup ? "onboarding-form__mode-button is-active" : "onboarding-form__mode-button"}
          type="button"
          aria-pressed={!isSetup}
          onClick={() => switchMode("login")}
        >
          ????
        </button>
      </div>

      <div className="onboarding-form__heading">
        <p className="onboarding-form__eyebrow">????????</p>
        <h1>{title}</h1>
        <p>
          {isSetup
            ? "???????????????????????? AI ????"
            : "?????????????? AI ?????????????"}
        </p>
      </div>

      <form onSubmit={submit} noValidate>
        <label className="onboarding-form__field" htmlFor="auth-username">
          <span>???</span>
          <input
            id="auth-username"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            placeholder="???momo"
            disabled={isSubmitting}
          />
        </label>

        <label className="onboarding-form__field" htmlFor="auth-password">
          <span>??</span>
          <input
            id="auth-password"
            type="password"
            autoComplete={isSetup ? "new-password" : "current-password"}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder={isSetup ? "?? 8 ?" : "??????"}
            disabled={isSubmitting}
          />
        </label>

        {error ? (
          <p className="onboarding-form__error" role="alert">
            {error}
          </p>
        ) : null}

        <EditorialButton className="onboarding-form__submit" type="submit" variant="accent" loading={isSubmitting} loadingLabel="?????">
          {submitLabel}
        </EditorialButton>
      </form>

      <p className="onboarding-form__privacy">???????????????????????????</p>
    </div>
  );
}

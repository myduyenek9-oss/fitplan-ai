import { OnboardingForm } from "../features/onboarding/OnboardingForm";

export type OnboardingPageProps = {
  onAuthenticated: () => void;
};

export function OnboardingPage({ onAuthenticated }: OnboardingPageProps) {
  return (
    <main className="onboarding-page">
      <section className="onboarding-page__story" aria-label="FitPlan AI ??">
        <div className="onboarding-page__brand">FitPlan AI<span>?</span></div>
        <div className="onboarding-page__story-copy">
          <p className="onboarding-page__eyebrow">???????????</p>
          <h2>??????????</h2>
          <p>
            ?????????????????FitPlan AI ?????????????????????????????
          </p>
        </div>

        <div className="onboarding-page__note" aria-label="FitPlan AI ??">
          <span className="onboarding-page__note-icon" aria-hidden="true">?</span>
          <div>
            <strong>??????</strong>
            <p>???????????? AI??????????????????</p>
          </div>
        </div>
      </section>

      <section className="onboarding-page__panel" aria-label="???????">
        <OnboardingForm onAuthenticated={onAuthenticated} />
      </section>
    </main>
  );
}

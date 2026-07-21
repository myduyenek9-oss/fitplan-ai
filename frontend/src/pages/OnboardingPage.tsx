import { OnboardingForm } from "../features/onboarding/OnboardingForm";

export type OnboardingPageProps = { onAuthenticated: () => void };

export function OnboardingPage({ onAuthenticated }: OnboardingPageProps) {
  return (
    <main className="onboarding-page">
      <section className="onboarding-page__story" aria-label="FitPlan AI 介绍">
        <div className="onboarding-page__brand">FitPlan AI<span>·</span></div>
        <div className="onboarding-page__story-copy">
          <p className="onboarding-page__eyebrow">每天一小步，改变会发生</p>
          <h2>吃得明白，练得刚好。</h2>
          <p>记录今天吃了什么、完成了多少运动。FitPlan AI 会把每一次临时变化，变成更适合你继续坚持的饮食和训练安排。</p>
        </div>
        <div className="onboarding-page__note" aria-label="FitPlan AI 功能">
          <span className="onboarding-page__note-icon" aria-hidden="true">✦</span>
          <div><strong>不是只算热量</strong><p>多吃了一块蛋糕？直接告诉 AI，它会补记并调整你今天接下来的计划。</p></div>
        </div>
      </section>
      <section className="onboarding-page__panel" aria-label="账号登录或创建"><OnboardingForm onAuthenticated={onAuthenticated} /></section>
    </main>
  );
}

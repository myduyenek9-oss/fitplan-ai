import type { MetricSummary } from "../lib/types";

export type MetricCardProps = MetricSummary & {
  className?: string;
};

export function MetricCard({ label, value, unit, detail, tone, className }: MetricCardProps) {
  const classes = ["metric-card", `metric-card--${tone}`, className].filter(Boolean).join(" ");

  return (
    <article className={classes}>
      <p className="metric-card__label">{label}</p>
      <p className="metric-card__value">
        {value}
        {unit ? <span className="metric-card__unit">{unit}</span> : null}
      </p>
      <p className="metric-card__detail">{detail}</p>
    </article>
  );
}

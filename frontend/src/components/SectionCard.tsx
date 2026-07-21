import type { ReactNode } from "react";

export type SectionCardProps = {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  className?: string;
  children: ReactNode;
};

export function SectionCard({ title, subtitle, action, className, children }: SectionCardProps) {
  const classes = ["section-card", className].filter(Boolean).join(" ");

  return (
    <section className={classes} aria-labelledby={`${title}-heading`}>
      <div className="section-card__header">
        <div>
          <h2 className="section-card__title" id={`${title}-heading`}>
            {title}
          </h2>
          {subtitle ? <p className="section-card__subtitle">{subtitle}</p> : null}
        </div>
        {action ? <div className="section-card__action">{action}</div> : null}
      </div>
      <div className="section-card__body">{children}</div>
    </section>
  );
}

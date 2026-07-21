import { forwardRef } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

export type EditorialButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "accent" | "secondary";
  loading?: boolean;
  loadingLabel?: string;
  icon?: ReactNode;
};

export const EditorialButton = forwardRef<HTMLButtonElement, EditorialButtonProps>(
  (
    {
      variant = "primary",
      loading = false,
      loadingLabel,
      icon,
      className,
      disabled,
      children,
      type,
      "aria-busy": ariaBusy,
      ...buttonProps
    },
    ref,
  ) => {
    const classes = ["editorial-button", `editorial-button--${variant}`, className]
      .filter(Boolean)
      .join(" ");

    return (
      <button
        {...buttonProps}
        ref={ref}
        className={classes}
        disabled={disabled || loading}
        type={type ?? "button"}
        aria-busy={loading ? "true" : ariaBusy}
      >
        {icon ? <span aria-hidden="true">{icon}</span> : null}
        {loading ? (loadingLabel ?? "处理中…") : children}
      </button>
    );
  },
);

EditorialButton.displayName = "EditorialButton";

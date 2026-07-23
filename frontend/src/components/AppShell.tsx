import type { ReactNode } from "react";
import type { NavKey } from "../lib/types";
import { BottomNav } from "./BottomNav";
import { SidebarNav } from "./SidebarNav";

export type AppShellProps = {
  title: string;
  subtitle?: string;
  eyebrow?: string;
  titleIcon?: boolean;
  activeNav?: NavKey;
  onNavigate?: (key: NavKey) => void;
  children: ReactNode;
};

export function AppShell({ title, subtitle, eyebrow, titleIcon = false, activeNav, onNavigate, children }: AppShellProps) {
  return (
    <div className="app-shell">
      <SidebarNav activeKey={activeNav} onNavigate={onNavigate} />

      <main className="app-shell__main">
        <div className="app-shell__content">
          <div className="app-shell__topbar" aria-label="FitPlan">
            <div className="app-shell__brand"><span aria-hidden="true">✦</span><strong>FitPlan</strong></div>
            <span className="app-shell__status"><i aria-hidden="true" />今日在线</span>
          </div>
          <header className="page-header">
            {eyebrow ? <p className="page-header__eyebrow">{eyebrow}</p> : null}
            <div className="page-header__title-row">
              {titleIcon ? <span className="heading-icon" aria-hidden="true">✦</span> : null}
              <h1 className="page-header__title">{title}</h1>
            </div>
            {subtitle ? <p className="page-header__subtitle">{subtitle}</p> : null}
          </header>

          {children}
        </div>
      </main>

      <BottomNav activeKey={activeNav} onNavigate={onNavigate} />
    </div>
  );
}

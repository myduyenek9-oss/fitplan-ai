import type { ReactNode } from "react";
import type { NavKey } from "../lib/types";
import { BottomNav } from "./BottomNav";
import { SidebarNav } from "./SidebarNav";

export type AppShellProps = {
  title: string;
  subtitle?: string;
  eyebrow?: string;
  activeNav?: NavKey;
  onNavigate?: (key: NavKey) => void;
  children: ReactNode;
};

export function AppShell({ title, subtitle, eyebrow, activeNav, onNavigate, children }: AppShellProps) {
  return (
    <div className="app-shell">
      <SidebarNav activeKey={activeNav} onNavigate={onNavigate} />

      <main className="app-shell__main">
        <div className="app-shell__content">
          <header className="page-header">
            {eyebrow ? <p className="page-header__eyebrow">{eyebrow}</p> : null}
            <h1 className="page-header__title">{title}</h1>
            {subtitle ? <p className="page-header__subtitle">{subtitle}</p> : null}
          </header>

          {children}
        </div>
      </main>

      <BottomNav activeKey={activeNav} onNavigate={onNavigate} />
    </div>
  );
}

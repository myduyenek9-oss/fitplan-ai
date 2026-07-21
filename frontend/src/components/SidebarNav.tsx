import type { NavKey } from "../lib/types";
import { DEFAULT_NAV_ITEMS } from "./BottomNav";

export type SidebarNavProps = {
  activeKey?: NavKey;
  onNavigate?: (key: NavKey) => void;
};

const noopNavigate = () => undefined;

export function SidebarNav({ activeKey, onNavigate = noopNavigate }: SidebarNavProps) {
  return (
    <aside className="sidebar-nav" aria-label="FitPlan AI">
      <div className="sidebar-nav__brand">FitPlan AI</div>

      <nav aria-label="主导航">
        <ul className="sidebar-nav__list">
          {DEFAULT_NAV_ITEMS.map((item) => (
            <li key={item.key} className="sidebar-nav__list-item">
              <button
                type="button"
                className="sidebar-nav__item"
                aria-current={activeKey === item.key ? "page" : undefined}
                onClick={() => onNavigate(item.key)}
              >
                <span aria-hidden="true">{item.icon}</span>
                <span>{item.label}</span>
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <section className="sidebar-nav__summary" aria-label="目标摘要">
        <p className="sidebar-nav__summary-label">本周目标：稳定减脂</p>
        <p className="sidebar-nav__summary-copy">保持热量赤字，优先完成三次力量训练。</p>
      </section>
    </aside>
  );
}

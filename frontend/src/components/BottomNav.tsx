import type { NavItem, NavKey } from "../lib/types";

export type BottomNavProps = {
  activeKey?: NavKey;
  onNavigate?: (key: NavKey) => void;
};

export const DEFAULT_NAV_ITEMS: NavItem[] = [
  { key: "home", label: "首页", icon: "⌂" },
  { key: "records", label: "记录", icon: "◷" },
  { key: "plans", label: "计划", icon: "✦" },
  { key: "coach", label: "AI 教练", icon: "◎" },
  { key: "settings", label: "我的", icon: "◌" },
];

const noopNavigate = () => undefined;

export function BottomNav({ activeKey, onNavigate = noopNavigate }: BottomNavProps) {
  return (
    <nav className="bottom-nav" aria-label="主导航">
      {DEFAULT_NAV_ITEMS.map((item) => (
        <button
          key={item.key}
          type="button"
          className="bottom-nav__item"
          aria-current={activeKey === item.key ? "page" : undefined}
          onClick={() => onNavigate(item.key)}
        >
          <span aria-hidden="true">{item.icon}</span>
          <span>{item.label}</span>
        </button>
      ))}
    </nav>
  );
}

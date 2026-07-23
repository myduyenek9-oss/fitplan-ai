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

type NavIconProps = { navKey: NavKey };

function NavIcon({ navKey }: NavIconProps) {
  const common = { fill: "none", stroke: "currentColor", strokeWidth: 1.9, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };

  if (navKey === "home") {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><path {...common} d="m3.5 10.5 8.5-7 8.5 7v9.2a1.8 1.8 0 0 1-1.8 1.8H5.3a1.8 1.8 0 0 1-1.8-1.8z" /><path {...common} d="M9 21.5v-6h6v6" /></svg>;
  }
  if (navKey === "records") {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><rect {...common} x="5" y="3.5" width="14" height="17" rx="2.4" /><path {...common} d="M8.5 8.5h7M8.5 12h7M8.5 15.5h4" /></svg>;
  }
  if (navKey === "plans") {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><path {...common} d="M12 20.5s7-3.9 7-10.3a4.1 4.1 0 0 0-7-2.9 4.1 4.1 0 0 0-7 2.9C5 16.6 12 20.5 12 20.5Z" /><path {...common} d="M9.2 12.1h5.6M12 9.3v5.6" /></svg>;
  }
  if (navKey === "coach") {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><path {...common} d="M12 3.5a8.5 8.5 0 0 0-8.5 8.5c0 2.1.8 4 2.1 5.5L5.1 21l3.6-1.2A8.5 8.5 0 1 0 12 3.5Z" /><path {...common} d="M9 12h.01M15 12h.01M9.2 15.3c1.7 1.2 3.9 1.2 5.6 0" /></svg>;
  }
  return <svg viewBox="0 0 24 24" aria-hidden="true"><circle {...common} cx="12" cy="8" r="3.6" /><path {...common} d="M4.7 20.5c.8-3.4 3.6-5.4 7.3-5.4s6.5 2 7.3 5.4" /></svg>;
}

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
          <span className="bottom-nav__icon" aria-hidden="true"><NavIcon navKey={item.key} /></span>
          <span className="bottom-nav__label">{item.label}</span>
        </button>
      ))}
    </nav>
  );
}

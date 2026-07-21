import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const srcRoot = resolve(__dirname);
const readSource = (relativePath: string) =>
  readFileSync(resolve(srcRoot, relativePath), "utf8");

describe("editorial visual system styles", () => {
  it("defines the editorial design tokens", () => {
    const tokens = readSource("styles/tokens.css");

    expect(tokens).toContain(":root");
    [
      "color-scheme: light;",
      'font-family: Inter, "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;',
      "--color-bg: #f6f1e8;",
      "--color-surface: #fffdf8;",
      "--color-surface-muted: #edf3e6;",
      "--color-surface-warm: #fff0dd;",
      "--color-primary: #123f34;",
      "--color-primary-strong: #0b2f27;",
      "--color-primary-soft: #dcebdd;",
      "--color-accent: #e48b4a;",
      "--color-accent-strong: #b65f28;",
      "--color-text: #1f2b26;",
      "--color-muted: #768078;",
      "--color-border: #deded2;",
      "--color-danger: #b84b3e;",
      "--shadow-soft: 0 16px 40px rgba(18, 63, 52, 0.09);",
      "--shadow-button: 0 8px 20px rgba(18, 63, 52, 0.14);",
      "--radius-card: 28px;",
      "--radius-control: 999px;",
      "--content-width: 1240px;",
      "--sidebar-width: 248px;",
      "--mobile-nav-height: 76px;",
    ].forEach((declaration) => expect(tokens).toContain(declaration));
  });

  it("imports tokens before global styles and the App", () => {
    const main = readSource("main.tsx");

    expect(main.indexOf('import "./styles/tokens.css";')).toBeGreaterThanOrEqual(0);
    expect(main.indexOf('import "./styles/global.css";')).toBeGreaterThan(
      main.indexOf('import "./styles/tokens.css";'),
    );
    expect(main.indexOf('import App from "./App";')).toBeGreaterThan(
      main.indexOf('import "./styles/global.css";'),
    );
  });

  it("provides shell layout, navigation, card, metric, and responsive selectors", () => {
    const global = readSource("styles/global.css");

    [
      "*,",
      "body",
      ":focus-visible",
      "button",
      "a",
      ".app-shell",
      ".app-shell__main",
      ".app-shell__content",
      ".page-header",
      ".page-header__eyebrow",
      ".page-header__title",
      ".page-header__subtitle",
      ".sidebar-nav",
      ".bottom-nav",
      ".bottom-nav__item",
      ".editorial-button",
      ".metric-grid",
      ".section-card",
    ].forEach((selector) => expect(global).toContain(selector));

    expect(global).toMatch(/\.sidebar-nav\s*\{[^}]*display:\s*none;/s);
    expect(global).toMatch(/padding-bottom:\s*calc\(var\(--mobile-nav-height\) \+ env\(safe-area-inset-bottom\)\);/);
    expect(global).toMatch(/@media\s*\(min-width:\s*960px\)\s*\{[\s\S]*\.app-shell\s*\{[\s\S]*padding-left:\s*var\(--sidebar-width\);[\s\S]*\.bottom-nav\s*\{[\s\S]*display:\s*none;/);
  });
});

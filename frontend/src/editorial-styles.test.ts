import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const srcRoot = resolve(__dirname);
const readSource = (relativePath: string) =>
  readFileSync(resolve(srcRoot, relativePath), "utf8");

const cssVariables = (css: string) => {
  const variables: Record<string, string> = {};

  for (const match of css.matchAll(/(--[\w-]+):\s*([^;]+);/g)) {
    variables[match[1]] = match[2].trim();
  }

  return variables;
};

const declarationBlock = (css: string, selector: string) => {
  const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`${escapedSelector}\\s*\\{(?<body>[^}]*)\\}`, "s").exec(css)
    ?.groups?.body ?? "";
};

const relativeLuminance = (hex: string) => {
  const channels = hex
    .replace("#", "")
    .match(/[\da-f]{2}/gi)
    ?.map((channel) => {
      const srgb = Number.parseInt(channel, 16) / 255;
      return srgb <= 0.03928
        ? srgb / 12.92
        : ((srgb + 0.055) / 1.055) ** 2.4;
    });

  if (!channels || channels.length !== 3) {
    throw new Error(`Expected a hex color, received ${hex}`);
  }

  return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
};

const contrastRatio = (foreground: string, background: string) => {
  const [lighter, darker] = [relativeLuminance(foreground), relativeLuminance(background)].sort(
    (a, b) => b - a,
  );

  return (lighter + 0.05) / (darker + 0.05);
};

describe("editorial visual system styles", () => {
  it("defines the required editorial token surface without snapshotting every value", () => {
    const tokens = readSource("styles/tokens.css");
    const vars = cssVariables(tokens);

    expect(declarationBlock(tokens, ":root")).toContain("color-scheme: light");
    expect(declarationBlock(tokens, ":root")).toContain(
      'font-family: Inter, "PingFang SC", "Microsoft YaHei", system-ui, sans-serif',
    );

    [
      "--color-bg",
      "--color-surface",
      "--color-surface-muted",
      "--color-surface-warm",
      "--color-primary",
      "--color-primary-strong",
      "--color-primary-soft",
      "--color-accent",
      "--color-accent-strong",
      "--color-text",
      "--color-muted",
      "--color-border",
      "--color-danger",
      "--shadow-soft",
      "--shadow-button",
      "--radius-card",
      "--radius-control",
      "--content-width",
      "--sidebar-width",
      "--mobile-nav-height",
      "--mobile-nav-gap",
    ].forEach((name) => expect(vars[name], `${name} token`).toBeDefined());

    expect(vars["--color-bg"]).toBe("#f4f8f5");
    expect(vars["--color-surface"]).toBe("#ffffff");
    expect(vars["--color-primary"]).toBe("#176b49");
    expect(vars["--mobile-nav-height"]).toBe("76px");
  });

  it("keeps normal-sized muted and strong accent copy at WCAG AA contrast", () => {
    const vars = cssVariables(readSource("styles/tokens.css"));
    const lightBackgrounds = [
      "--color-bg",
      "--color-surface",
      "--color-surface-muted",
      "--color-surface-warm",
    ];

    for (const foreground of ["--color-muted", "--color-accent-strong"]) {
      for (const background of lightBackgrounds) {
        expect(
          contrastRatio(vars[foreground], vars[background]),
          `${foreground} on ${background}`,
        ).toBeGreaterThanOrEqual(4.5);
      }
    }
  });

  it("imports tokens before global styles and the App", () => {
    const main = readSource("main.tsx");
    const tokensImport = main.indexOf('import "./styles/tokens.css";');
    const globalImport = main.indexOf('import "./styles/global.css";');
    const appImport = main.indexOf('import App from "./App";');

    expect(tokensImport).toBeGreaterThanOrEqual(0);
    expect(globalImport).toBeGreaterThan(tokensImport);
    expect(appImport).toBeGreaterThan(globalImport);
  });

  it("provides required shell, navigation, card, metric, focus, and responsive rules", () => {
    const global = readSource("styles/global.css");

    [
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

    expect(declarationBlock(global, "*::after")).toContain("box-sizing: border-box");
    expect(declarationBlock(global, "body")).toContain("var(--color-bg)");
    expect(declarationBlock(global, "button")).toContain("cursor: pointer");
    expect(declarationBlock(global, "a")).toContain("text-decoration: none");

    expect(global).not.toMatch(/:focus\s*\{[^}]*outline:\s*none\s*;/s);
    expect(declarationBlock(global, ":focus")).toMatch(/outline:\s*\d+px\s+solid/);
    expect(global).toMatch(/:focus:not\(:focus-visible\)\s*\{[^}]*outline:\s*none\s*;/s);
    expect(declarationBlock(global, ":focus-visible")).toContain("outline-offset");

    expect(declarationBlock(global, ".sidebar-nav")).toContain("display: none");
    expect(declarationBlock(global, ".app-shell__main")).toMatch(
      /padding-bottom:\s*calc\(var\(--mobile-nav-height\) \+ var\(--mobile-nav-gap\) \+ env\(safe-area-inset-bottom\)\)/,
    );
    expect(declarationBlock(global, ".bottom-nav")).toContain("var(--mobile-nav-gap)");
    expect(global).toMatch(/@media\s*\(min-width:\s*960px\)[\s\S]*\.bottom-nav\s*\{[^}]*display:\s*none;/);
  });

  it("defines editorial button accent and hover states without applying hover styles to disabled buttons", () => {
    const global = readSource("styles/global.css");

    expect(declarationBlock(global, ".editorial-button--accent")).toContain("var(--color-accent)");
    expect(declarationBlock(global, ".editorial-button--accent:not(:disabled):hover")).toContain(
      "var(--color-accent-strong)",
    );
    expect(declarationBlock(global, ".editorial-button:not(:disabled):hover")).toContain(
      "transform: translateY(-1px)",
    );
    expect(declarationBlock(global, ".editorial-button--secondary:not(:disabled):hover")).toContain(
      "var(--color-surface-muted)",
    );
    expect(global).not.toContain(".editorial-button:hover");
    expect(global).not.toContain(".editorial-button--secondary:hover");
    expect(global).not.toContain(".editorial-button--accent:hover");
  });
  it("defines complete desktop sidebar descendant styles", () => {
    const global = readSource("styles/global.css");

    [
      ".sidebar-nav__brand",
      ".sidebar-nav__list",
      ".sidebar-nav__list-item",
      ".sidebar-nav__item",
      ".sidebar-nav__item[aria-current=\"page\"]",
      ".sidebar-nav__summary",
      ".sidebar-nav__summary-label",
      ".sidebar-nav__summary-copy",
    ].forEach((selector) => {
      expect(declarationBlock(global, selector), `${selector} block`).not.toBe("");
    });

    expect(declarationBlock(global, ".sidebar-nav__list")).toContain("list-style: none");
    expect(declarationBlock(global, ".sidebar-nav__list")).toContain("padding: 0");
    expect(declarationBlock(global, ".sidebar-nav__item")).toContain("display: inline-flex");
    expect(declarationBlock(global, ".sidebar-nav__item")).toContain("align-items: center");
    expect(declarationBlock(global, ".sidebar-nav__item[aria-current=\"page\"]")).toContain(
      "var(--color-primary-soft)",
    );
    expect(declarationBlock(global, ".sidebar-nav__summary")).toContain("margin-top: auto");
  });
});

# Frontend Editorial Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the responsive editorial-style FitPlan AI frontend shell with reusable capsule buttons, cards, navigation, API/type foundations, and a static magazine dashboard preview.

**Architecture:** Keep presentational components small and data-free. `AppShell` owns only the responsive page frame and navigation composition; `App.tsx` supplies static preview data until later tasks connect real API state. CSS variables in `tokens.css` define the palette and dimensions, while `global.css` defines reset, typography, layout utilities, and responsive behavior. The API module is a minimal typed fetch wrapper with no secrets or business logic.

**Tech Stack:** React 19, TypeScript, Vite, Vitest, Testing Library, plain CSS.

---

### Task 1: Define the shared frontend data contracts

**Files:**
- Create: `frontend/src/lib/types.ts`

- [ ] **Step 1: Add the type definitions used by the shell and preview**

Create `frontend/src/lib/types.ts` with these exact contracts:

```ts
export type NavKey = "home" | "records" | "plans" | "coach" | "settings";

export interface NavItem {
  key: NavKey;
  label: string;
  icon: string;
}

export interface MetricSummary {
  label: string;
  value: string;
  unit?: string;
  detail: string;
  tone: "green" | "orange" | "cream";
}

export interface DailyPlanSummary {
  goalLabel: string;
  calorieTarget: number;
  caloriesConsumed: number;
  exerciseTarget: string;
  completionLabel: string;
}

export interface RecordSummary {
  id: string;
  category: "food" | "exercise";
  title: string;
  detail: string;
  calories: number;
  time: string;
}

export interface AiSuggestion {
  title: string;
  body: string;
  actionLabel: string;
}
```

- [ ] **Step 2: Run the typecheck before any consumer exists**

Run `npm run build` from `frontend`. Expected: the existing app still compiles successfully and the new type-only module introduces no errors.

- [ ] **Step 3: Commit the contracts**

```powershell
git add frontend/src/lib/types.ts
git commit -m "feat: define frontend preview types"
```

---

### Task 2: Add the typed API client foundation

**Files:**
- Create: `frontend/src/lib/api.ts`

- [ ] **Step 1: Implement a minimal JSON request helper**

Create `frontend/src/lib/api.ts` with an environment-based base URL, a typed error, and a generic request function:

```ts
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  details: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

async function parseResponse(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return response.text();
  }
  return response.json();
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  const payload = await parseResponse(response);
  if (!response.ok) {
    const message = typeof payload === "object" && payload !== null && "detail" in payload
      ? String((payload as { detail: unknown }).detail)
      : `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status, payload);
  }
  return payload as T;
}
```

Ensure caller-provided `headers`, credentials, and method are not accidentally discarded by the merge order. The helper must remain safe to import when `VITE_API_BASE_URL` is empty so Vite proxy-relative requests work in development.

- [ ] **Step 2: Verify the frontend build**

Run `npm run build` from `frontend`. Expected: PASS.

- [ ] **Step 3: Commit the API foundation**

```powershell
git add frontend/src/lib/api.ts
git commit -m "feat: add frontend api client foundation"
```

---

### Task 3: Add visual tokens and global responsive styles

**Files:**
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/styles/global.css`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: Create the design tokens**

Create `frontend/src/styles/tokens.css` with warm off-white, deep green, warm orange, typography, radius, shadow, and responsive variables:

```css
:root {
  color-scheme: light;
  font-family: Inter, "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
  --color-bg: #f6f1e8;
  --color-surface: #fffdf8;
  --color-surface-muted: #edf3e6;
  --color-surface-warm: #fff0dd;
  --color-primary: #123f34;
  --color-primary-strong: #0b2f27;
  --color-primary-soft: #dcebdd;
  --color-accent: #e48b4a;
  --color-accent-strong: #b65f28;
  --color-text: #1f2b26;
  --color-muted: #768078;
  --color-border: #deded2;
  --color-danger: #b84b3e;
  --shadow-soft: 0 16px 40px rgba(18, 63, 52, 0.09);
  --shadow-button: 0 8px 20px rgba(18, 63, 52, 0.14);
  --radius-card: 28px;
  --radius-control: 999px;
  --content-width: 1240px;
  --sidebar-width: 248px;
  --mobile-nav-height: 76px;
}
```

- [ ] **Step 2: Add global reset and layout classes**

Create `frontend/src/styles/global.css` with a box-sizing reset, body background, accessible focus styles, button/link defaults, shell layout classes, card typography, metric grid, and mobile safe-area padding. Include a media query at `min-width: 960px` that reserves the sidebar and hides `.bottom-nav`, and a default mobile rule that hides `.sidebar-nav`.

The CSS must include these selectors because later components rely on them:

```css
.app-shell
.app-shell__main
.app-shell__content
.page-header
.page-header__eyebrow
.page-header__title
.page-header__subtitle
.sidebar-nav
.bottom-nav
.bottom-nav__item
.editorial-button
.metric-grid
.section-card
```

- [ ] **Step 3: Import both styles globally**

Modify `frontend/src/main.tsx` so the imports are:

```ts
import "./styles/tokens.css";
import "./styles/global.css";
```

before rendering `App`.

- [ ] **Step 4: Run tests and build**

Run `npm run test -- --run` and `npm run build` from `frontend`. Expected: existing tests pass and production build succeeds.

- [ ] **Step 5: Commit the visual foundation**

```powershell
git add frontend/src/styles frontend/src/main.tsx
git commit -m "feat: add editorial visual tokens"
```

---

### Task 4: Implement and test the Editorial Capsule button

**Files:**
- Create: `frontend/src/components/EditorialButton.tsx`
- Create: `frontend/src/components/EditorialButton.test.tsx`

- [ ] **Step 1: Write the failing component tests**

Create tests that verify all of the following:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { EditorialButton } from "./EditorialButton";

describe("EditorialButton", () => {
  it("renders the primary variant with its accessible name", () => {
    render(<EditorialButton variant="primary">记录饮食</EditorialButton>);
    expect(screen.getByRole("button", { name: "记录饮食" })).toHaveClass("editorial-button--primary");
  });

  it("renders secondary and accent variants", () => {
    const { rerender } = render(<EditorialButton variant="secondary">记录运动</EditorialButton>);
    expect(screen.getByRole("button", { name: "记录运动" })).toHaveClass("editorial-button--secondary");
    rerender(<EditorialButton variant="accent">和 AI 调整计划</EditorialButton>);
    expect(screen.getByRole("button", { name: "和 AI 调整计划" })).toHaveClass("editorial-button--accent");
  });

  it("prevents interaction while disabled or loading", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    const { rerender } = render(
      <EditorialButton onClick={onClick} disabled>保存计划</EditorialButton>,
    );
    const button = screen.getByRole("button", { name: "保存计划" });
    expect(button).toBeDisabled();
    await user.click(button);
    expect(onClick).not.toHaveBeenCalled();

    rerender(
      <EditorialButton onClick={onClick} loading loadingLabel="正在保存">保存计划</EditorialButton>,
    );
    expect(screen.getByRole("button", { name: "正在保存" })).toBeDisabled();
  });
});
```

Because `userEvent` is not currently installed, add `@testing-library/user-event` to `frontend/package.json` and run `npm install` before running this test.

- [ ] **Step 2: Run the focused test to verify it fails**

Run `npm run test -- --run src/components/EditorialButton.test.tsx` from `frontend`. Expected: FAIL because the component and dependency do not exist yet.

- [ ] **Step 3: Implement the minimal typed button**

Create a `forwardRef<HTMLButtonElement, EditorialButtonProps>` component. `EditorialButtonProps` must extend `ButtonHTMLAttributes<HTMLButtonElement>` and define:

```ts
variant?: "primary" | "accent" | "secondary";
loading?: boolean;
loadingLabel?: string;
icon?: ReactNode;
```

When `loading` is true, render `loadingLabel ?? "处理中…"`, set `disabled`, set `aria-busy="true"`, and preserve the button's native type. Render the optional icon in a `span` with `aria-hidden="true"`. Merge the matching modifier class with `editorial-button` and any caller-supplied `className`.

- [ ] **Step 4: Run the focused test to verify it passes**

Run `npm run test -- --run src/components/EditorialButton.test.tsx`. Expected: PASS.

- [ ] **Step 5: Commit the button**

```powershell
git add frontend/src/components/EditorialButton.tsx frontend/src/components/EditorialButton.test.tsx frontend/package.json frontend/package-lock.json
 git commit -m "feat: add editorial capsule button"
```

---

### Task 5: Implement navigation and shell components

**Files:**
- Create: `frontend/src/components/BottomNav.tsx`
- Create: `frontend/src/components/SidebarNav.tsx`
- Create: `frontend/src/components/AppShell.tsx`

- [ ] **Step 1: Implement the shared navigation list**

Use the `NavItem[]` contract from Task 1 and provide these default items in both navigation components:

```ts
const defaultItems: NavItem[] = [
  { key: "home", label: "首页", icon: "⌂" },
  { key: "records", label: "记录", icon: "◷" },
  { key: "plans", label: "计划", icon: "✦" },
  { key: "coach", label: "AI 教练", icon: "◎" },
  { key: "settings", label: "我的", icon: "◌" },
];
```

`BottomNav` should render a `nav` with `aria-label="主导航"`, a list of buttons or links with active state, and the `.bottom-nav__item` class. `SidebarNav` should render the same accessible labels in a desktop `<aside>` with `.sidebar-nav`.

- [ ] **Step 2: Implement the responsive AppShell composition**

`AppShell` props must include:

```ts
title: string;
subtitle?: string;
eyebrow?: string;
activeNav?: NavKey;
children: ReactNode;
```

Render `<SidebarNav />`, a `.app-shell__main` wrapper, a `.page-header`, the `.app-shell__content` children, and `<BottomNav />`. Both nav components should accept an `onNavigate?: (key: NavKey) => void` callback, defaulting to no-op, so the shell remains presentational.

- [ ] **Step 3: Run tests and build**

Run `npm run test -- --run` and `npm run build` from `frontend`. Expected: PASS.

- [ ] **Step 4: Commit the shell components**

```powershell
git add frontend/src/components/AppShell.tsx frontend/src/components/BottomNav.tsx frontend/src/components/SidebarNav.tsx
git commit -m "feat: add responsive app navigation shell"
```

---

### Task 6: Implement reusable cards and the magazine dashboard preview

**Files:**
- Create: `frontend/src/components/MetricCard.tsx`
- Create: `frontend/src/components/SectionCard.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Implement `MetricCard` and `SectionCard`**

`MetricCard` accepts `MetricSummary` plus optional `className`. Render label, value, optional unit, and detail with a tone modifier class such as `metric-card--green`.

`SectionCard` accepts `title`, optional `subtitle`, optional `action`, optional `className`, and `children`. Render the action area only when supplied and keep the content in a semantic `<section>` with an accessible heading.

- [ ] **Step 2: Replace the minimal App with the approved static preview**

Use `AppShell` and the exact content from the spec. The page must include:

- eyebrow `今日 · 轻盈记录`
- title `今天离目标更近一点`
- subtitle `减脂 · 轻强度训练周`
- a daily plan hero with `1850 kcal`, `已摄入 1280`, `剩余 570`, and `快走 30 分钟 + 上肢训练`
- three `EditorialButton` actions with accessible names `记录饮食`, `记录运动`, `和 AI 调整计划`
- at least three metric cards
- a today records section with food and exercise rows
- an AI suggestion section containing `如果晚餐想吃得满足`

Keep the data as local constants typed with the contracts from `frontend/src/lib/types.ts`. Do not fetch from the API client in this task.

- [ ] **Step 3: Update the App test for semantic product content**

Keep the `FitPlan AI` brand assertion through the shell and add assertions for `今天离目标更近一点`, `记录饮食`, `和 AI 调整计划`, and `如果晚餐想吃得满足`.

- [ ] **Step 4: Run all frontend tests and build**

Run:

```powershell
npm run test -- --run
npm run build
```

Expected: all tests pass and Vite produces `frontend/dist`.

- [ ] **Step 5: Commit the dashboard preview**

```powershell
git add frontend/src/App.tsx frontend/src/App.test.tsx frontend/src/components/MetricCard.tsx frontend/src/components/SectionCard.tsx
 git commit -m "feat: add editorial dashboard preview"
```

---

### Task 7: Perform visual and responsive verification

**Files:**
- Modify: `frontend/src/styles/global.css` only if verification reveals a concrete layout defect

- [ ] **Step 1: Run the production checks**

From `frontend`, run:

```powershell
npm run test -- --run
npm run build
```

Expected: all frontend tests pass and the production build succeeds.

- [ ] **Step 2: Start the local preview server**

Run `npm run dev -- --host 127.0.0.1` from `frontend` and open the reported local URL in the in-app browser.

- [ ] **Step 3: Verify mobile presentation**

At a mobile viewport, confirm the static home page shows the warm background, card flow, capsule actions, and fixed bottom navigation without content being hidden behind it.

- [ ] **Step 4: Verify desktop presentation**

At a desktop viewport, confirm the left sidebar is visible, bottom navigation is hidden, main content is constrained, and the two-column editorial dashboard is readable.

- [ ] **Step 5: Commit any concrete verification-only fixes**

If a layout defect was found and fixed, run the production checks again and commit with:

```powershell
git add frontend/src/styles/global.css
 git commit -m "fix: tune responsive editorial layout"
```

If no defect is found, do not create an empty commit.

---

## Plan self-review

- Spec coverage: Tasks 1–2 cover the type and API foundations; Task 3 covers tokens and global responsive rules; Task 4 covers the capsule button and its required tests; Task 5 covers responsive navigation and shell composition; Task 6 covers reusable cards and every required static dashboard content item; Task 7 covers build and visual verification.
- Placeholder scan: no `TODO`, `TBD`, or unspecified implementation steps are used; all commands, files, selectors, props, and expected outcomes are concrete.
- Type consistency: `NavKey`, `NavItem`, `MetricSummary`, `DailyPlanSummary`, `RecordSummary`, and `AiSuggestion` are defined in Task 1 and consumed with the same names and fields in Tasks 5–6. `EditorialButton` props are defined in Task 4 and used consistently in Task 6.

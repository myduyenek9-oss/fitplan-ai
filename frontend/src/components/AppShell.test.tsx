import userEvent from "@testing-library/user-event";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AppShell } from "./AppShell";
import { BottomNav } from "./BottomNav";
import { SidebarNav } from "./SidebarNav";

const navLabels = ["首页", "记录", "计划", "AI 教练", "我的"];

afterEach(() => {
  cleanup();
});

describe("BottomNav", () => {
  it("renders the default primary navigation items and marks the active page", () => {
    render(<BottomNav activeKey="plans" />);

    const nav = screen.getByRole("navigation", { name: "主导航" });

    for (const label of navLabels) {
      expect(within(nav).getByRole("button", { name: new RegExp(label) })).toBeInTheDocument();
    }

    expect(within(nav).getByRole("button", { name: /计划/ })).toHaveClass("bottom-nav__item");
    expect(within(nav).getByRole("button", { name: /计划/ })).toHaveAttribute("aria-current", "page");
  });

  it("notifies callers when an item is selected", async () => {
    const user = userEvent.setup();
    const handleNavigate = vi.fn();

    render(<BottomNav activeKey="home" onNavigate={handleNavigate} />);

    await user.click(screen.getByRole("button", { name: /AI 教练/ }));

    expect(handleNavigate).toHaveBeenCalledWith("coach");
  });
});

describe("SidebarNav", () => {
  it("renders the desktop landmark, brand, default navigation, and target summary", () => {
    render(<SidebarNav activeKey="records" />);

    const sidebar = screen.getByRole("complementary", { name: "FitPlan AI" });
    const nav = within(sidebar).getByRole("navigation", { name: "主导航" });

    expect(within(sidebar).getByText("FitPlan AI")).toBeInTheDocument();
    expect(within(sidebar).getByText(/本周目标：稳定减脂/)).toBeInTheDocument();

    for (const label of navLabels) {
      expect(within(nav).getByRole("button", { name: new RegExp(label) })).toBeInTheDocument();
    }

    expect(within(nav).getByRole("button", { name: /记录/ })).toHaveAttribute("aria-current", "page");
  });
});

describe("AppShell", () => {
  it("wraps page content with responsive navigation and an editorial page header", () => {
    render(
      <AppShell
        eyebrow="今日概览"
        title="营养计划"
        titleIcon
        subtitle="记录饮食、训练和 AI 建议。"
        activeNav="home"
      >
        <section>核心内容</section>
      </AppShell>,
    );

    expect(screen.getByRole("heading", { name: "营养计划", level: 1 })).toBeInTheDocument();
    expect(document.querySelector(".page-header__title-row .heading-icon")).toHaveTextContent("✦");
    expect(screen.getByText("今日概览")).toHaveClass("page-header__eyebrow");
    expect(screen.getByText("记录饮食、训练和 AI 建议。")).toHaveClass("page-header__subtitle");
    expect(screen.getByText("核心内容")).toBeInTheDocument();
    expect(screen.getAllByRole("navigation", { name: "主导航" })).toHaveLength(2);
  });

  it("forwards shell navigation selections from both responsive navs", async () => {
    const user = userEvent.setup();
    const handleNavigate = vi.fn();

    render(
      <AppShell title="导航联动" activeNav="home" onNavigate={handleNavigate}>
        <section>核心内容</section>
      </AppShell>,
    );

    const navigations = screen.getAllByRole("navigation", { name: "主导航" });

    await user.click(within(navigations[0]).getByRole("button", { name: /计划/ }));
    await user.click(within(navigations[1]).getByRole("button", { name: /AI 教练/ }));

    expect(handleNavigate).toHaveBeenNthCalledWith(1, "plans");
    expect(handleNavigate).toHaveBeenNthCalledWith(2, "coach");
  });
});

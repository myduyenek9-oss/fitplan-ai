import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { CoachMarkdown } from "./CoachMarkdown";

describe("CoachMarkdown", () => {
  afterEach(cleanup);

  it("renders headings, bold text, lists and special guidance cards", () => {
    const { container } = render(<CoachMarkdown content={
      "## 调整建议\n今天以 **恢复** 为主。\n- 补水 500ml\n- 提前休息\n\n### 风险提醒\n如果疼痛加重，请停止训练。\n\n### 今日行动建议\n1. 轻松走路 15 分钟\n2. 晚餐补充蛋白质"
    } />);

    expect(screen.getByRole("heading", { name: "调整建议" })).toBeInTheDocument();
    expect(screen.getByText("恢复").tagName).toBe("STRONG");
    expect(screen.getByText("补水 500ml")).toBeInTheDocument();
    expect(container.querySelector(".coach-markdown-card--risk")).toHaveTextContent("风险提醒");
    expect(container.querySelector(".coach-markdown-card--action")).toHaveTextContent("今日行动建议");
    expect(container.textContent).not.toContain("###");
    expect(container.textContent).not.toContain("**");
  });

  it("renders raw html as text instead of injecting it", () => {
    const { container } = render(<CoachMarkdown content={'<img src=x onerror="alert(1)">'} />);
    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByText('<img src=x onerror="alert(1)">')).toBeInTheDocument();
  });
});

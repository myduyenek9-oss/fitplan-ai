import userEvent from "@testing-library/user-event";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { EditorialButton } from "./EditorialButton";

describe("EditorialButton", () => {
  it("renders a primary button with an accessible name and editorial classes by default", () => {
    render(<EditorialButton>生成计划</EditorialButton>);

    const button = screen.getByRole("button", { name: "生成计划" });

    expect(button).toHaveClass("editorial-button", "editorial-button--primary");
    expect(button).not.toBeDisabled();
  });

  it("supports secondary and accent variants", () => {
    render(
      <>
        <EditorialButton variant="secondary">返回</EditorialButton>
        <EditorialButton variant="accent">保存偏好</EditorialButton>
      </>,
    );

    expect(screen.getByRole("button", { name: "返回" })).toHaveClass(
      "editorial-button",
      "editorial-button--secondary",
    );
    expect(screen.getByRole("button", { name: "保存偏好" })).toHaveClass(
      "editorial-button",
      "editorial-button--accent",
    );
  });

  it("prevents interaction when disabled", async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();

    render(
      <EditorialButton disabled onClick={handleClick}>
        不可用
      </EditorialButton>,
    );

    await user.click(screen.getByRole("button", { name: "不可用" }));

    expect(handleClick).not.toHaveBeenCalled();
  });

  it("shows a loading label, marks busy, and disables interaction while loading", async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();

    render(
      <EditorialButton loading loadingLabel="正在生成" onClick={handleClick}>
        生成计划
      </EditorialButton>,
    );

    const button = screen.getByRole("button", { name: "正在生成" });

    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");

    await user.click(button);

    expect(handleClick).not.toHaveBeenCalled();
  });
});

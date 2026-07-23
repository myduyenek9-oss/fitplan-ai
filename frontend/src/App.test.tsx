import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { beforeEach } from "vitest";
import { DashboardPreview } from "./App";

describe("App", () => {
  beforeEach(() => {
  });

  it("renders the editorial dashboard preview", () => {
    render(<DashboardPreview />);

    expect(screen.getAllByText("FitPlan AI")[0]).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "今天离目标更近一点" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "记录饮食" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "和 AI 调整计划" })[0]).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /./ })).toBeInTheDocument();
    expect(screen.getByText("\u8fd0\u52a8\u6d88\u8017")).toBeInTheDocument();
    expect(screen.getByText("\u8102\u80aa")).toBeInTheDocument();
    expect(screen.getByText(/先记录你的第一餐/)).toBeInTheDocument();
  });
});

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("App", () => {
  it("renders the editorial dashboard preview", () => {
    render(<App />);

    expect(screen.getAllByText("FitPlan AI")[0]).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "今天离目标更近一点" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "记录饮食" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "和 AI 调整计划" })).toBeInTheDocument();
    expect(screen.getByText(/如果晚餐想吃得满足/)).toBeInTheDocument();
  });
});

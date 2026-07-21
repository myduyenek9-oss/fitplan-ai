import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { beforeEach } from "vitest";
import { ACCESS_TOKEN_STORAGE_KEY } from "./lib/api";
import App from "./App";

describe("App", () => {
  beforeEach(() => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, "test-token");
  });

  it("renders the editorial dashboard preview", () => {
    render(<App />);

    expect(screen.getAllByText("FitPlan AI")[0]).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "今天离目标更近一点" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "记录饮食" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "和 AI 调整计划" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /./ })).toBeInTheDocument();
    expect(screen.getByText(/如果晚餐想吃得满足/)).toBeInTheDocument();
  });
});

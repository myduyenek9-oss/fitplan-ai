import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PlansPage } from "./PlansPage";

const plan = {
  id: 7,
  user_id: 1,
  title: "我的 7 天饮食训练计划",
  start_date: "2026-07-21",
  end_date: "2026-07-27",
  is_active: true,
  created_at: "2026-07-21T08:00:00Z",
  updated_at: "2026-07-21T08:00:00Z",
  days: Array.from({ length: 7 }, (_, index) => ({
    date: "2026-07-" + String(21 + index).padStart(2, "0"),
    calorie_target: 1850,
    meals: [{ name: "燕麦酸奶碗", meal_type: "breakfast", calories: 420, protein_g: 28, carb_g: 42, fat_g: 12 }],
    training_instruction: { kind: "workout", title: "全身力量训练", instructions: "深蹲、推举和划船各 3 组。", duration_minutes: 45 },
  })),
};

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), { status, headers: { "content-type": "application/json" } });
}

describe("PlansPage", () => {
  afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

  it("shows an empty state and generates a 7-day plan", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse({ detail: "Plan not found" }, 404))
      .mockResolvedValueOnce(jsonResponse(plan, 201));
    vi.stubGlobal("fetch", fetchMock);
    const onNavigate = vi.fn();

    render(<PlansPage onNavigate={onNavigate} />);
    expect(await screen.findByRole("heading", { name: "让 AI 按你的目标排好接下来的 7 天" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "生成我的 7 天计划" }));
    expect(await screen.findByText("我的 7 天饮食训练计划")).toBeInTheDocument();
    expect(screen.getByText("燕麦酸奶碗")).toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(["/api/plans/current", "/api/plans/generate"]);

    fireEvent.click(screen.getByRole("button", { name: "和 AI 调整计划" }));
    expect(onNavigate).toHaveBeenCalledWith("coach");
  });

  it("changes the visible day when a day tab is selected", async () => {
    const secondDayPlan = { ...plan, days: plan.days.map((item, index) => index === 1 ? { ...item, meals: [{ ...item.meals[0], name: "鸡胸杂粮饭" }] } : item) };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(secondDayPlan)));
    render(<PlansPage onNavigate={vi.fn()} />);
    await screen.findByText("燕麦酸奶碗");

    fireEvent.click(screen.getByRole("tab", { name: /第 2 天/ }));
    await waitFor(() => expect(screen.getByText("鸡胸杂粮饭")).toBeInTheDocument());
  });
});

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
    expect(document.querySelector(".plan-header-card__eyebrow-row .heading-icon")).toHaveTextContent("✦");
    expect(screen.getByText("燕麦酸奶碗")).toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(["/api/plans/current", "/api/plans/generate"]);

    fireEvent.click(screen.getByRole("button", { name: "和 AI 调整计划" }));
    expect(onNavigate).toHaveBeenCalledWith("coach");
  });

  it("localizes legacy fallback plan text that was saved in English", async () => {
    const legacyPlan = {
      ...plan,
      days: plan.days.map((item) => ({
        ...item,
        meals: [{ ...item.meals[0], name: "Balanced meal 1" }],
        training_instruction: { kind: "workout", title: "Full-body strength", instructions: "Complete a moderate strength session", duration_minutes: 40 },
      })),
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(legacyPlan)));
    render(<PlansPage onNavigate={vi.fn()} />);

    expect(await screen.findByText("\u5747\u8861\u5348\u9910 \u00b7 \u7b2c 1 \u5929")).toBeInTheDocument();
    expect(screen.getAllByText("\u5168\u8eab\u529b\u91cf\u8bad\u7ec3").length).toBeGreaterThan(0);
    expect(screen.queryByText("Balanced meal 1")).not.toBeInTheDocument();
  });

  it("localizes a legacy postponed recovery split", async () => {
    const legacyRecoveryPlan = {
      ...plan,
      days: plan.days.map((item, index) => index === 5
        ? { ...item, training_instruction: { kind: "rest", title: "\u6062\u590d\u5b89\u6392", instructions: "\u8f7b\u6d3b\u52a8\u4e0e\u6062\u590d", duration_minutes: 25, split: "??????" } }
        : item),
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(legacyRecoveryPlan)));
    render(<PlansPage onNavigate={vi.fn()} />);

    fireEvent.click((await screen.findAllByRole("tab"))[5]);
    expect(await screen.findByText(/\u6062\u590d\u4e0e\u6d3b\u52a8\u5ea6/)).toBeInTheDocument();
    expect(screen.getByText(/25 \u5206\u949f/)).toBeInTheDocument();
  });

  it("changes the visible day when a day tab is selected", async () => {
    const secondDayPlan = { ...plan, days: plan.days.map((item, index) => index === 1 ? { ...item, meals: [{ ...item.meals[0], name: "鸡胸杂粮饭" }] } : item) };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(secondDayPlan)));
    render(<PlansPage onNavigate={vi.fn()} />);
    await screen.findByText("燕麦酸奶碗");

    fireEvent.click(screen.getByRole("tab", { name: /第 2 天/ }));
    await waitFor(() => expect(screen.getByText("鸡胸杂粮饭")).toBeInTheDocument());
  });

  it("defaults to today's plan day and uses a different encouragement for each day", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(plan)));
    render(<PlansPage onNavigate={vi.fn()} />);

    const today = new Date();
    const offset = today.getTimezoneOffset() * 60_000;
    const todayString = new Date(today.getTime() - offset).toISOString().slice(0, 10);
    const selectedIndex = Math.max(0, plan.days.findIndex((day) => day.date === todayString));
    const encouragements = [
      "\u4e0d\u9700\u8981\u4e00\u6b21\u505a\u5230\u5b8c\u7f8e\uff0c\u5148\u5b8c\u6210\u4eca\u5929\u6700\u91cd\u8981\u7684\u4e00\u6b65\u3002",
      "\u628a\u8282\u594f\u653e\u6162\u4e00\u70b9\uff0c\u7a33\u5b9a\u5b8c\u6210\u6bd4\u5076\u5c14\u62fc\u547d\u66f4\u6709\u6548\u3002",
      "\u4eca\u5929\u7ed9\u81ea\u5df1\u7559\u4e00\u70b9\u4f59\u5730\uff0c\u505a\u5230\u4e03\u516b\u6210\u4e5f\u503c\u5f97\u80af\u5b9a\u3002",
    ];
    expect(await screen.findByText(encouragements[selectedIndex % encouragements.length])).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: /\u7b2c 2 \u5929/ }));
    await waitFor(() => expect(screen.getByText(encouragements[1])).toBeInTheDocument());
    expect(screen.queryByText(encouragements[selectedIndex % encouragements.length])).not.toBeInTheDocument();
  });

});

import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RecordsPage } from "./RecordsPage";

function summary(overrides: Record<string, unknown> = {}) {
  return {
    date: "2026-07-21",
    goal: { daily_calories: 1850, protein_g: 110, carb_g: 200, fat_g: 55 },
    food_totals: { calories: 420, protein_g: 28, carb_g: 42, fat_g: 12 },
    exercise_totals: { calories_burned: 0, duration_minutes: 0 },
    remaining_calories: 1430,
    macro_completion_percentages: { protein_g: 25, carb_g: 21, fat_g: 22 },
    food_status_counts: { active: 1, deleted: 0, undone: 0 },
    food_records: [{ id: 1, user_id: 1, original_text: "燕麦酸奶碗", parsed_content: {}, meal_type: "breakfast", calories: 420, protein_g: 28, carb_g: 42, fat_g: 12, status: "active", logged_at: "2026-07-21T08:20:00+08:00", created_at: "2026-07-21T00:20:00Z", updated_at: "2026-07-21T00:20:00Z" }],
    exercise_records: [],
    ...overrides,
  };
}

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), { status, headers: { "content-type": "application/json" } });
}

describe("RecordsPage", () => {
  afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); });

  it("adds an exercise from natural language and refreshes the daily totals", async () => {
    const initial = summary();
    const afterExercise = summary({ exercise_totals: { calories_burned: 210, duration_minutes: 35 }, remaining_calories: 1640, exercise_records: [{ id: 9, user_id: 1, exercise_type: "快走", description: "晚上快走 35 分钟", duration_minutes: 35, calories_burned: 210, logged_at: "2026-07-21T20:00:00+08:00", created_at: "2026-07-21T12:00:00Z", updated_at: "2026-07-21T12:00:00Z" }] });
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse(initial))
      .mockResolvedValueOnce(jsonResponse({ record: afterExercise.exercise_records[0], daily_summary: afterExercise, adjustment_suggestion: "今晚做一点拉伸，记得补水。", conversation_id: 3 }, 201));
    vi.stubGlobal("fetch", fetchMock);

    render(<RecordsPage onNavigate={vi.fn()} />);
    expect(await screen.findByText("燕麦酸奶碗")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "补充运动记录" }), { target: { value: "晚上快走 35 分钟" } });
    fireEvent.click(screen.getByRole("button", { name: "记录运动" }));

    expect(await screen.findByText("今晚做一点拉伸，记得补水。")).toBeInTheDocument();
    expect(screen.getByText("快走")).toBeInTheDocument();
    const today = new Date();
    const offset = today.getTimezoneOffset() * 60_000;
    const expectedDate = new Date(today.getTime() - offset).toISOString().slice(0, 10);
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([`/api/records/daily?date=${expectedDate}`, "/api/records/exercise/natural-language"]);
  });

  it("撤销运动记录后会刷新当日汇总", async () => {
    const exerciseRecord = {
      id: 9,
      user_id: 1,
      exercise_type: "测试划船",
      description: "临时测试记录",
      duration_minutes: 35,
      calories_burned: 210,
      logged_at: "2026-07-21T20:00:00+08:00",
      created_at: "2026-07-21T12:00:00Z",
      updated_at: "2026-07-21T12:00:00Z",
    };
    const initial = summary({
      exercise_totals: { calories_burned: 210, duration_minutes: 35 },
      remaining_calories: 1640,
      exercise_records: [exerciseRecord],
    });
    const afterUndo = summary({
      exercise_totals: { calories_burned: 0, duration_minutes: 0 },
      remaining_calories: 1430,
      exercise_records: [],
    });
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse(initial))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(jsonResponse(afterUndo));
    vi.stubGlobal("fetch", fetchMock);

    render(<RecordsPage onNavigate={vi.fn()} />);
    const exerciseName = await screen.findByText("测试划船");
    const exerciseItem = exerciseName.closest("article");
    expect(exerciseItem).not.toBeNull();
    fireEvent.click(within(exerciseItem as HTMLElement).getByRole("button", { name: "撤销" }));

    expect(await screen.findByText("已撤销这条运动记录，今日运动消耗和剩余热量已重新计算。")).toBeInTheDocument();
    expect(screen.queryByText("测试划船")).not.toBeInTheDocument();
    const today = new Date();
    const offset = today.getTimezoneOffset() * 60_000;
    const expectedDate = new Date(today.getTime() - offset).toISOString().slice(0, 10);
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      `/api/records/daily?date=${expectedDate}`,
      "/api/records/exercise/9/undo",
      `/api/records/daily?date=${expectedDate}`,
    ]);
  });

  it("shows food records from morning to evening using the effective displayed minute", async () => {
    const mixed = summary({
      food_status_counts: { active: 4, deleted: 0, undone: 0 },
      food_records: [
        { id: 1, user_id: 1, original_text: "早餐", parsed_content: {}, meal_type: "breakfast", calories: 300, protein_g: 20, carb_g: 30, fat_g: 10, status: "active", logged_at: "2026-07-21T09:59:00+08:00", created_at: "2026-07-21T01:59:00Z", updated_at: "2026-07-21T01:59:00Z" },
        { id: 2, user_id: 1, original_text: "下午加餐", parsed_content: {}, meal_type: "snack", calories: 200, protein_g: 10, carb_g: 20, fat_g: 8, status: "active", logged_at: "2026-07-21T16:01:00+08:00", created_at: "2026-07-21T08:01:00Z", updated_at: "2026-07-21T08:01:00Z" },
        { id: 3, user_id: 1, original_text: "晚餐", parsed_content: {}, meal_type: "dinner", calories: 500, protein_g: 30, carb_g: 50, fat_g: 18, status: "active", logged_at: "2026-07-21T19:21:00+08:00", created_at: "2026-07-21T11:21:00Z", updated_at: "2026-07-21T11:21:00Z" },
        { id: 4, user_id: 1, original_text: "晚间牛奶", parsed_content: { source: "ai" }, meal_type: "snack", calories: 150, protein_g: 8, carb_g: 12, fat_g: 5, status: "active", logged_at: "2026-07-21T19:00:00+08:00", created_at: "2026-07-21T19:43:00+08:00", updated_at: "2026-07-21T19:43:00+08:00" },
      ],
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(jsonResponse(mixed)));
    const { container } = render(<RecordsPage onNavigate={vi.fn()} />);
    await screen.findByText("晚间牛奶");
    const foodCard = Array.from(container.querySelectorAll(".section-card")).find((card) => card.textContent?.includes("饮食记录"));
    const names = Array.from(foodCard?.querySelectorAll(".records-timeline__item h3") ?? []).map((node) => node.textContent);
    expect(names).toEqual(["早餐", "下午加餐", "晚餐", "晚间牛奶"]);
  });
});

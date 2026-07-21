import { cleanup, fireEvent, render, screen } from "@testing-library/react";
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
  afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

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
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(["/api/records/daily?date=2026-07-21", "/api/records/exercise/natural-language"]);
  });
});

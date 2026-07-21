import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { QuickRecordComposer } from "./QuickRecordComposer";
import { logFoodFromText } from "../../lib/fitplan-api";

vi.mock("../../lib/fitplan-api", () => ({
  logFoodFromText: vi.fn(),
}));

const logFoodFromTextMock = vi.mocked(logFoodFromText);

const result = {
  record: {
    id: 12,
    user_id: 1,
    original_text: "刚才多吃了一块蛋糕",
    parsed_content: {},
    meal_type: "snack",
    calories: 280,
    protein_g: 4,
    carb_g: 38,
    fat_g: 12,
    status: "active" as const,
    logged_at: "2026-07-21T10:00:00+08:00",
    created_at: "2026-07-21T10:00:00+08:00",
    updated_at: "2026-07-21T10:00:00+08:00",
  },
  daily_summary: {
    date: "2026-07-21",
    goal: null,
    food_totals: { calories: 280, protein_g: 4, carb_g: 38, fat_g: 12 },
    exercise_totals: { calories_burned: 0, duration_minutes: 0 },
    remaining_calories: null,
    macro_completion_percentages: { protein_g: null, carb_g: null, fat_g: null },
    food_status_counts: { active: 1, deleted: 0, undone: 0 },
    food_records: [],
    exercise_records: [],
  },
  adjustment_suggestion: "晚餐少一点油脂，再补一份优质蛋白。",
  conversation_id: 9,
};

describe("QuickRecordComposer", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("submits natural language food and shows the returned adjustment", async () => {
    const user = userEvent.setup();
    const onRecorded = vi.fn();
    logFoodFromTextMock.mockResolvedValue(result);

    render(<QuickRecordComposer date="2026-07-21" onRecorded={onRecorded} />);

    await user.type(screen.getByRole("textbox", { name: "补充饮食记录" }), "刚才多吃了一块蛋糕");
    await user.click(screen.getByRole("button", { name: "记录并调整" }));

    await waitFor(() => {
      expect(logFoodFromTextMock).toHaveBeenCalledWith("刚才多吃了一块蛋糕", "2026-07-21");
    });

    expect(await screen.findByText("已记录约 280 kcal")).toBeInTheDocument();
    expect(screen.getByText("晚餐少一点油脂，再补一份优质蛋白。")).toBeInTheDocument();
    expect(onRecorded).toHaveBeenCalledWith(result);
  });

  it("keeps the input and explains the failure when AI parsing fails", async () => {
    const user = userEvent.setup();
    logFoodFromTextMock.mockRejectedValue(new Error("AI 服务暂不可用"));

    render(<QuickRecordComposer date="2026-07-21" />);

    const input = screen.getByRole("textbox", { name: "补充饮食记录" });
    await user.type(input, "喝了一杯奶茶");
    fireEvent.click(screen.getByRole("button", { name: "记录并调整" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("AI 服务暂不可用");
    expect(input).toHaveValue("喝了一杯奶茶");
  });
});

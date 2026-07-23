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
  recorded_exercise: null,
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
    expect(screen.getByRole("button", { name: "\u8bb0\u5f55\u5e76\u8c03\u6574" })).toHaveClass("editorial-button--dingtalk-action");

    await user.type(screen.getByRole("textbox", { name: "补充饮食或运动记录" }), "刚才多吃了一块蛋糕");
    await user.click(screen.getByRole("button", { name: "记录并调整" }));

    await waitFor(() => {
      expect(logFoodFromTextMock).toHaveBeenCalledWith("刚才多吃了一块蛋糕", "2026-07-21");
    });

    expect(await screen.findByText("已记录饮食约 280 kcal")).toBeInTheDocument();
    expect(screen.getByText("晚餐少一点油脂，再补一份优质蛋白。")).toBeInTheDocument();
    expect(onRecorded).toHaveBeenCalledWith(result);
  });

  it("shows separate diet and exercise calories for a mixed record", async () => {
    const user = userEvent.setup();
    const onRecorded = vi.fn();
    const mixedResult = {
      ...result,
      record: { ...result.record, original_text: "刚刚吃了两个烧烤", calories: 200 },
      recorded_exercise: {
        id: 18,
        user_id: 1,
        original_text: "慢跑了十分钟",
        exercise_type: "慢跑",
        description: "慢跑了十分钟",
        duration_minutes: 10,
        calories_burned: 75,
        logged_at: "2026-07-22T20:00:00+08:00",
        created_at: "2026-07-22T20:00:00+08:00",
        updated_at: "2026-07-22T20:00:00+08:00",
      },
      daily_summary: {
        ...result.daily_summary,
        food_totals: { calories: 200, protein_g: 12, carb_g: 10, fat_g: 12 },
        exercise_totals: { calories_burned: 75, duration_minutes: 10 },
      },
    };
    logFoodFromTextMock.mockResolvedValue(mixedResult);

    render(<QuickRecordComposer date="2026-07-22" onRecorded={onRecorded} />);

    await user.type(
      screen.getByRole("textbox", { name: "补充饮食或运动记录" }),
      "刚刚吃了两个烧烤 慢跑了十分钟",
    );
    await user.click(screen.getByRole("button", { name: "记录并调整" }));

    expect(await screen.findByText("已记录饮食约 200 kcal")).toBeInTheDocument();
    expect(screen.getByText("已记录运动约 75 kcal")).toBeInTheDocument();
    expect(onRecorded).toHaveBeenCalledWith(mixedResult);
  });

  it("shows pure exercise as a burned-calorie record instead of food intake", async () => {
    const user = userEvent.setup();
    const pureExerciseResult = {
      ...result,
      record: {
        id: 19,
        user_id: 1,
        original_text: "我慢跑了",
        exercise_type: "running",
        description: "慢跑 10 分钟",
        duration_minutes: 10,
        calories_burned: 80,
        logged_at: "2026-07-23T08:30:00+08:00",
        created_at: "2026-07-23T08:30:00+08:00",
        updated_at: "2026-07-23T08:30:00+08:00",
      },
      recorded_exercise: {
        id: 19,
        user_id: 1,
        original_text: "我慢跑了",
        exercise_type: "running",
        description: "慢跑 10 分钟",
        duration_minutes: 10,
        calories_burned: 80,
        logged_at: "2026-07-23T08:30:00+08:00",
        created_at: "2026-07-23T08:30:00+08:00",
        updated_at: "2026-07-23T08:30:00+08:00",
      },
      daily_summary: {
        ...result.daily_summary,
        food_totals: { calories: 0, protein_g: 0, carb_g: 0, fat_g: 0 },
        exercise_totals: { calories_burned: 80, duration_minutes: 10 },
      },
    };
    logFoodFromTextMock.mockResolvedValue(pureExerciseResult);

    render(<QuickRecordComposer date="2026-07-23" />);
    await user.type(screen.getByRole("textbox", { name: "补充饮食或运动记录" }), "我慢跑了");
    await user.click(screen.getByRole("button", { name: "记录并调整" }));

    expect(await screen.findByText("已记录运动约 80 kcal")).toBeInTheDocument();
    expect(screen.queryByText(/已记录饮食约/)).not.toBeInTheDocument();
  });

  it("keeps the input and explains the failure when AI parsing fails", async () => {
    const user = userEvent.setup();
    logFoodFromTextMock.mockRejectedValue(new Error("AI 服务暂不可用"));

    render(<QuickRecordComposer date="2026-07-21" />);

    const input = screen.getByRole("textbox", { name: "补充饮食或运动记录" });
    await user.type(input, "喝了一杯奶茶");
    fireEvent.click(screen.getByRole("button", { name: "记录并调整" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("AI 服务暂不可用");
    expect(input).toHaveValue("喝了一杯奶茶");
  });
});

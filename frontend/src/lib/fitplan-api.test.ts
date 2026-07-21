import { afterEach, describe, expect, it, vi } from "vitest";
import { getDailySummary, logFoodFromText } from "./fitplan-api";

describe("fitplan API", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads a daily summary using an ISO date query", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ date: "2026-07-21" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getDailySummary("2026-07-21")).resolves.toEqual({ date: "2026-07-21" });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/records/daily?date=2026-07-21",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("submits natural language food with the selected date", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ adjustment_suggestion: "晚餐减少油脂。" }), {
        status: 201,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(logFoodFromText("下午多吃了一块蛋糕", "2026-07-21")).resolves.toEqual({
      adjustment_suggestion: "晚餐减少油脂。",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/records/food/natural-language",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ text: "下午多吃了一块蛋糕", today: "2026-07-21" }),
      }),
    );
  });
});

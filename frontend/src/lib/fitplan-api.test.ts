import { afterEach, describe, expect, it, vi } from "vitest";
import { getDailySummary, logExerciseFromText, logFoodFromText } from "./fitplan-api";

function response(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), { status, headers: { "content-type": "application/json" } });
}

describe("fitplan API", () => {
  afterEach(() => { vi.unstubAllGlobals(); });

  it("loads a daily summary using an ISO date query", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response({ date: "2026-07-21" }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(getDailySummary("2026-07-21")).resolves.toEqual({ date: "2026-07-21" });
    expect(fetchMock).toHaveBeenCalledWith("/api/records/daily?date=2026-07-21", expect.objectContaining({ credentials: "include" }));
  });

  it("submits natural language food with the selected date", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response({ adjustment_suggestion: "晚餐减少油脂。" }, 201));
    vi.stubGlobal("fetch", fetchMock);
    await expect(logFoodFromText("下午多吃了一块蛋糕", "2026-07-21")).resolves.toEqual({ adjustment_suggestion: "晚餐减少油脂。" });
    expect(fetchMock).toHaveBeenCalledWith("/api/records/food/natural-language", expect.objectContaining({ method: "POST", body: JSON.stringify({ text: "下午多吃了一块蛋糕", today: "2026-07-21" }) }));
  });

  it("submits natural language exercise with the selected date", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response({ adjustment_suggestion: "训练后补充蛋白质。" }, 201));
    vi.stubGlobal("fetch", fetchMock);
    await expect(logExerciseFromText("晚上快走 35 分钟", "2026-07-21")).resolves.toEqual({ adjustment_suggestion: "训练后补充蛋白质。" });
    expect(fetchMock).toHaveBeenCalledWith("/api/records/exercise/natural-language", expect.objectContaining({ method: "POST", body: JSON.stringify({ text: "晚上快走 35 分钟", today: "2026-07-21" }) }));
  });
});

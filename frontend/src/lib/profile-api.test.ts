import { afterEach, describe, expect, it, vi } from "vitest";
import { previewCalorieTargets, upsertGoal, upsertProfile } from "./profile-api";

function response(payload: unknown) { return new Response(JSON.stringify(payload), { status: 200, headers: { "content-type": "application/json" } }); }

describe("profile and goal API", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("sends calorie calculation inputs to the preview endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response({ daily_calories: 1850 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(previewCalorieTargets({ age: 30, sex: "female", weight_kg: 58, height_cm: 165, activity_level: "moderate", goal: "fat_loss" })).resolves.toEqual({ daily_calories: 1850 });
    expect(fetchMock).toHaveBeenCalledWith("/api/calorie/preview", expect.objectContaining({ method: "POST", body: expect.stringContaining('"age":30') }));
  });
  it("saves profile and calculated goal through protected endpoints", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(response({ id: 1 })));
    vi.stubGlobal("fetch", fetchMock);
    await upsertProfile({ display_name: "test", sex: "female", birth_date: "1996-04-10", height_cm: 165, timezone: "Asia/Shanghai" });
    await upsertGoal({ goal_type: "fat_loss", daily_calories: 1850, protein_g: 100, carb_g: 210, fat_g: 55, activity_level: "moderate" });
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(["/api/profile", "/api/profile/goal"]);
  });
});

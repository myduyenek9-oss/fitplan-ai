import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { InitialSetupPage } from "./InitialSetupPage";

function jsonResponse(payload: unknown, status = 200) { return new Response(JSON.stringify(payload), { status, headers: { "content-type": "application/json" } }); }

describe("InitialSetupPage", () => {
  afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
  it("calculates targets and saves profile, goal, and initial weight", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(jsonResponse({ bmr: 1320, tdee: 2046, daily_calories: 1750, protein_g: 105, carb_g: 190, fat_g: 55 })).mockResolvedValueOnce(jsonResponse({ id: 1 })).mockResolvedValueOnce(jsonResponse({ id: 1 })).mockResolvedValueOnce(jsonResponse({ id: 1 }, 201));
    vi.stubGlobal("fetch", fetchMock);
    const completed = vi.fn(); const user = userEvent.setup();
    render(<InitialSetupPage onCompleted={completed} />);
    await user.type(document.getElementById("profile-birthdate") as HTMLInputElement, "1996-04-10");
    await user.type(document.getElementById("profile-height") as HTMLInputElement, "165");
    await user.type(document.getElementById("profile-weight") as HTMLInputElement, "58.5");
    await user.click(document.querySelector('button[type="submit"]') as HTMLButtonElement);
    await waitFor(() => expect(completed).toHaveBeenCalledTimes(1));
    expect(screen.getByRole("status")).toHaveTextContent("1750");
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(["/api/calorie/preview", "/api/profile", "/api/profile/goal", "/api/body-metrics"]);
  });
  it("loads saved profile data when editing and avoids duplicate weight entries", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse({ display_name: "Xiaoman", sex: "female", birth_date: "1996-04-10", height_cm: 165 }))
      .mockResolvedValueOnce(jsonResponse({ goal_type: "fat_loss", daily_calories: 1750, protein_g: 105, carb_g: 190, fat_g: 55, activity_level: "moderate", target_weight_kg: 55, target_date: "2026-12-31" }))
      .mockResolvedValueOnce(jsonResponse([{ id: 7, weight_kg: 58.5 }]))
      .mockResolvedValueOnce(jsonResponse({ is_configured: false, is_enabled: false, webhook_hint: null, has_signing_secret: false, keyword: null, created_at: null, updated_at: null }))
      .mockResolvedValueOnce(jsonResponse({ bmr: 1320, tdee: 2046, daily_calories: 1750, protein_g: 105, carb_g: 190, fat_g: 55 }))
      .mockResolvedValueOnce(jsonResponse({ id: 1 }))
      .mockResolvedValueOnce(jsonResponse({ id: 1 }));
    vi.stubGlobal("fetch", fetchMock);
    const completed = vi.fn();
    const user = userEvent.setup();
    render(<InitialSetupPage isEditing onCompleted={completed} />);

    await waitFor(() => expect((document.getElementById("profile-name") as HTMLInputElement).value).toBe("Xiaoman"));
    expect((document.getElementById("profile-height") as HTMLInputElement).value).toBe("165");
    expect((document.getElementById("profile-weight") as HTMLInputElement).value).toBe("58.5");
    expect((document.getElementById("profile-target-weight") as HTMLInputElement).value).toBe("55");
    expect(document.querySelector('button[type="submit"]')).toBeInTheDocument();
    expect(screen.queryByText("FitPlan AI·")).not.toBeInTheDocument();
    expect(screen.queryByText("我的资料 · 随时更新")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "让计划继续 贴合现在的你。" })).toBeInTheDocument();
    expect(screen.getByText("建议使用真实、近期的体重数据。目标不是绝对限制，而是让你看见可以持续的方向。")).toBeInTheDocument();
    expect(document.querySelector(".initial-setup-page__editing-note .initial-setup-page__tip")).toBeInTheDocument();
    expect(screen.queryByText("这里会显示你已保存的健康资料和目标。修改后保存，今日热量、营养素与 AI 建议会立即同步更新。")).not.toBeInTheDocument();
    expect(document.querySelectorAll(".initial-setup-page__tip")).toHaveLength(1);
    expect(await screen.findByText("未绑定")).toBeInTheDocument();

    await user.click(document.querySelector('button[type="submit"]') as HTMLButtonElement);
    await waitFor(() => expect(completed).toHaveBeenCalledTimes(1));
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "/api/profile",
      "/api/profile/goal",
      "/api/body-metrics",
      "/api/notifications/dingtalk",
      "/api/calorie/preview",
      "/api/profile",
      "/api/profile/goal",
    ]);
  });

  it("shows validation before making a calculation request", async () => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    render(<InitialSetupPage onCompleted={vi.fn()} />);
    fireEvent.click(document.querySelector('button[type="button"]') as HTMLButtonElement);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

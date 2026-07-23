import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CoachPage } from "./CoachPage";

function jsonResponse(payload: unknown) {
  return new Response(JSON.stringify(payload), { status: 200, headers: { "content-type": "application/json" } });
}

describe("CoachPage", () => {
  afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

  it("loads saved messages and appends an AI response", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse([{ id: 1, role: "user", content: "昨天加班没训练", created_at: "2026-07-20T10:00:00Z" }]))
      .mockResolvedValueOnce(jsonResponse({ reply: "今天做 20 分钟轻量训练即可。", conversation_id: 2, user_message_id: 3, user_created_at: "2026-07-20T18:00:00+08:00", assistant_created_at: "2026-07-20T18:00:05+08:00", recorded_exercise: null, daily_summary: null }));
    vi.stubGlobal("fetch", fetchMock);
    render(<CoachPage onNavigate={vi.fn()} />);

    expect(await screen.findByText("昨天加班没训练")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "我的头像" })).toHaveAttribute("src", "/avatars/user-avatar.jpg");
    expect(document.querySelector(".coach-guide__eyebrow")).toHaveTextContent("✦今天不用重新开始");
    fireEvent.change(screen.getByRole("textbox", { name: "告诉 AI 教练你的变化" }), { target: { value: "今天也只能练 20 分钟" } });
    fireEvent.click(screen.getByRole("button", { name: "发送给 AI" }));

    expect(await screen.findByText("今天做 20 分钟轻量训练即可。")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "AI 教练头像" })).toHaveAttribute("src", "/avatars/ai-coach-avatar.jpg");
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(["/api/ai/history", "/api/ai/chat"]);
  });

  it("renders AI markdown and confirms an exercise saved from chat", async () => {
    const recordedExercise = {
      id: 8, user_id: 1, original_text: "我刚跑了30分钟", exercise_type: "慢跑", description: "轻松慢跑",
      duration_minutes: 30, calories_burned: 240, logged_at: "2026-07-22T19:20:00+08:00",
      created_at: "2026-07-22T11:20:00Z", updated_at: "2026-07-22T11:20:00Z",
    };
    const recordedFood = {
      id: 7, user_id: 1, original_text: "中午吃了一碗饭和猪肝", parsed_content: {}, meal_type: "lunch",
      calories: 460, protein_g: 26, carb_g: 66, fat_g: 11, status: "active", logged_at: "2026-07-22T12:10:00+08:00",
      created_at: "2026-07-22T11:20:00Z", updated_at: "2026-07-22T11:20:00Z",
    };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse({
        reply: "### 今日行动建议\n- **补水** 500ml\n- 做 5 分钟拉伸",
        conversation_id: 9, user_message_id: 8, user_created_at: "2026-07-22T19:20:00+08:00", assistant_created_at: "2026-07-22T19:20:06+08:00", recorded_food: recordedFood, recorded_exercise: recordedExercise, daily_summary: null,
      }));
    vi.stubGlobal("fetch", fetchMock);
    const { container } = render(<CoachPage onNavigate={vi.fn()} />);

    await screen.findByText("从今天最真实的变化开始说吧。");
    fireEvent.change(screen.getByRole("textbox", { name: "告诉 AI 教练你的变化" }), { target: { value: "我刚跑了30分钟" } });
    fireEvent.click(screen.getByRole("button", { name: "发送给 AI" }));

    expect(await screen.findByText("已同步到饮食记录")).toBeInTheDocument();
    expect(screen.getByText("中午吃了一碗饭和猪肝 · 约 460 kcal")).toBeInTheDocument();
    expect(await screen.findByText("已同步到运动记录")).toBeInTheDocument();
    expect(screen.getByText("慢跑 · 30 分钟 · 约 240 kcal")).toBeInTheDocument();
    expect(container.querySelector(".coach-markdown-card--action")).toHaveTextContent("今日行动建议");
    expect(screen.getByText("补水").tagName).toBe("STRONG");
    expect(container.textContent).not.toContain("###");
  });

  it("shows a saved confirmation after the AI really postpones training", async () => {
    const adjustment = {
      action: "postpone_training",
      status: "applied",
      plan_id: 3,
      source_date: "2026-07-23",
      target_date: "2026-07-24",
      message: "\u5df2\u5c067\u670823\u65e5\u7684\u8bad\u7ec3\u987a\u5ef6\u52307\u670824\u65e5\uff0c\u539f\u65e5\u671f\u5df2\u6539\u4e3a\u8f7b\u6d3b\u52a8\u4e0e\u6062\u590d\uff0c\u540e\u7eed\u8bad\u7ec3\u4e5f\u5df2\u4f9d\u6b21\u987a\u5ef6\u5e76\u4fdd\u5b58\u3002",
    };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse({
        reply: "\u5df2\u7ecf\u5e2e\u4f60\u987a\u5ef6\u5e76\u4fdd\u5b58\u3002",
        conversation_id: 12,
        user_message_id: 11,
        user_created_at: "2026-07-23T13:20:00+08:00",
        assistant_created_at: "2026-07-23T13:20:06+08:00",
        recorded_food: null,
        recorded_exercise: null,
        daily_summary: null,
        plan_adjustment: adjustment,
      }));
    vi.stubGlobal("fetch", fetchMock);
    const { container } = render(<CoachPage onNavigate={vi.fn()} />);

    await screen.findByText("\u4ece\u4eca\u5929\u6700\u771f\u5b9e\u7684\u53d8\u5316\u5f00\u59cb\u8bf4\u5427\u3002");
    fireEvent.change(screen.getByRole("textbox", { name: "\u544a\u8bc9 AI \u6559\u7ec3\u4f60\u7684\u53d8\u5316" }), {
      target: { value: "\u628a\u6211\u660e\u5929\u7684\u8bad\u7ec3\u8ba1\u5212\u5ef6\u8fdf\u4e00\u5929" },
    });
    fireEvent.click(screen.getByRole("button", { name: "\u53d1\u9001\u7ed9 AI" }));

    expect(await screen.findByText("\u8bad\u7ec3\u8ba1\u5212\u5df2\u66f4\u65b0")).toBeInTheDocument();
    expect(screen.getByText(adjustment.message)).toBeInTheDocument();
    expect(container.querySelector(".coach-plan-sync--applied")).toBeInTheDocument();
  });

  it("renders a meal replacement confirmation without calling it a workout update", async () => {
    const adjustment = {
      action: "replace_meal",
      status: "applied",
      plan_id: 3,
      source_date: "2026-07-23",
      target_date: "2026-07-23",
      meal_type: "dinner",
      previous_meal_name: "Original salmon dinner",
      updated_meal_name: "Replacement tofu dinner",
      message: "Only tonight's dinner was replaced.",
    };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse({
        reply: "\u5df2\u5e2e\u4f60\u53ea\u66ff\u6362\u4eca\u665a\u665a\u9910\u3002",
        conversation_id: 13,
        user_message_id: 12,
        user_created_at: "2026-07-23T13:21:00+08:00",
        assistant_created_at: "2026-07-23T13:21:08+08:00",
        recorded_food: null,
        recorded_exercise: null,
        daily_summary: null,
        plan_adjustment: adjustment,
      }));
    vi.stubGlobal("fetch", fetchMock);
    const { container } = render(<CoachPage onNavigate={vi.fn()} />);

    await screen.findByText("\u4ece\u4eca\u5929\u6700\u771f\u5b9e\u7684\u53d8\u5316\u5f00\u59cb\u8bf4\u5427\u3002");
    fireEvent.change(screen.getByRole("textbox", { name: "\u544a\u8bc9 AI \u6559\u7ec3\u4f60\u7684\u53d8\u5316" }), {
      target: { value: "\u628a\u4eca\u665a\u665a\u9910\u6362\u4e00\u4e0b" },
    });
    fireEvent.click(screen.getByRole("button", { name: "\u53d1\u9001\u7ed9 AI" }));

    expect(await screen.findByText("\u9910\u98df\u5b89\u6392\u5df2\u66f4\u65b0")).toBeInTheDocument();
    const syncNotice = container.querySelector(".coach-plan-sync");
    expect(syncNotice).toHaveTextContent(adjustment.message);
    expect(syncNotice).toHaveTextContent(/\u5df2\u4fdd\u7559\u5176\u4ed6\u9910\u6b21\u3001\u8bad\u7ec3\u548c\u65e5\u671f\u4e0d\u53d8/);
    expect(container.textContent).not.toContain("\u8bad\u7ec3\u8ba1\u5212\u5df2\u66f4\u65b0");
  });

  it("shows persisted user-timezone dates and exact message times", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(jsonResponse([
      { id: 1, role: "user", content: "day-one-user", created_at: "2026-07-22T13:24:07+08:00" },
      { id: 2, role: "assistant", content: "day-one-assistant", created_at: "2026-07-22T13:24:12+08:00" },
      { id: 3, role: "user", content: "day-two-user", created_at: "2026-07-23T08:15:31+08:00" },
    ]));
    vi.stubGlobal("fetch", fetchMock);
    render(<CoachPage onNavigate={vi.fn()} />);

    expect(await screen.findByText("2026\u5e747\u670822\u65e5")).toBeInTheDocument();
    expect(screen.getByText("2026\u5e747\u670823\u65e5")).toBeInTheDocument();
    expect(screen.getByText("13:24:07")).toBeInTheDocument();
    expect(screen.getByText("13:24:12")).toBeInTheDocument();
    expect(screen.getByText("08:15:31")).toBeInTheDocument();
    expect(document.querySelector('time[datetime="2026-07-22T13:24:07+08:00"]')).toBeInTheDocument();
  });



  it("uses persisted server timestamps after sending a message", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse({
        reply: "Server-timed reply",
        conversation_id: 12,
        user_message_id: 11,
        user_created_at: "2026-07-23T13:24:07+08:00",
        assistant_created_at: "2026-07-23T13:24:12+08:00",
        recorded_food: null,
        recorded_exercise: null,
        daily_summary: null,
        plan_adjustment: null,
      }));
    vi.stubGlobal("fetch", fetchMock);
    render(<CoachPage onNavigate={vi.fn()} />);

    await screen.findByText("从今天最真实的变化开始说吧。");
    fireEvent.change(screen.getByRole("textbox", { name: "告诉 AI 教练你的变化" }), {
      target: { value: "A server-timed message" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送给 AI" }));

    expect(await screen.findByText("Server-timed reply")).toBeInTheDocument();
    expect(screen.getByText("13:24:07")).toHaveAttribute("dateTime", "2026-07-23T13:24:07+08:00");
    expect(screen.getByText("13:24:12")).toHaveAttribute("dateTime", "2026-07-23T13:24:12+08:00");
  });

  it("deletes selected chat messages", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse([
        { id: 1, role: "user", content: "keep-message", created_at: "2026-07-23T09:00:00+08:00" },
        { id: 2, role: "assistant", content: "delete-message", created_at: "2026-07-23T09:00:05+08:00" },
      ]))
      .mockResolvedValueOnce(jsonResponse({ deleted_count: 1 }));
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("confirm", vi.fn(() => true));
    render(<CoachPage onNavigate={vi.fn()} />);

    await screen.findByText("delete-message");
    fireEvent.click(screen.getByRole("button", { name: "选择删除" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "选择聊天记录：delete-message" }));
    fireEvent.click(screen.getByRole("button", { name: "删除所选" }));

    await waitFor(() => expect(screen.queryByText("delete-message")).not.toBeInTheDocument());
    expect(screen.getByText("keep-message")).toBeInTheDocument();
    expect(fetchMock.mock.calls[1][0]).toBe("/api/ai/history/delete");
    expect(fetchMock.mock.calls[1][1]).toMatchObject({
      method: "POST",
      body: JSON.stringify({ message_ids: [2] }),
    });
  });

  it("clears all chat messages", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse([
        { id: 1, role: "user", content: "message-to-clear", created_at: "2026-07-23T09:00:00+08:00" },
      ]))
      .mockResolvedValueOnce(jsonResponse({ deleted_count: 1 }));
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("confirm", vi.fn(() => true));
    render(<CoachPage onNavigate={vi.fn()} />);

    await screen.findByText("message-to-clear");
    fireEvent.click(screen.getByRole("button", { name: "一键清空" }));

    expect(await screen.findByText("从今天最真实的变化开始说吧。")).toBeInTheDocument();
    expect(fetchMock.mock.calls[1][0]).toBe("/api/ai/history");
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: "DELETE" });
  });

});

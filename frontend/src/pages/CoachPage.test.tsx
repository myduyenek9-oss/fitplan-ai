import { cleanup, fireEvent, render, screen } from "@testing-library/react";
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
      .mockResolvedValueOnce(jsonResponse({ reply: "今天做 20 分钟轻量训练即可。", conversation_id: 2 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<CoachPage onNavigate={vi.fn()} />);

    expect(await screen.findByText("昨天加班没训练")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "告诉 AI 教练你的变化" }), { target: { value: "今天也只能练 20 分钟" } });
    fireEvent.click(screen.getByRole("button", { name: "发送给 AI" }));

    expect(await screen.findByText("今天做 20 分钟轻量训练即可。")).toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(["/api/ai/history", "/api/ai/chat"]);
  });
});

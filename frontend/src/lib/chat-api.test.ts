import { afterEach, describe, expect, it, vi } from "vitest";
import { getChatHistory, sendChatMessage } from "./chat-api";

function response(payload: unknown) {
  return new Response(JSON.stringify(payload), { status: 200, headers: { "content-type": "application/json" } });
}

describe("chat API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("reads saved messages and sends a dated question", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(response([])));
    vi.stubGlobal("fetch", fetchMock);
    await getChatHistory();
    await sendChatMessage("今天吃多了", "2026-07-21");
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(["/api/ai/history", "/api/ai/chat"]);
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: "POST", body: expect.stringContaining("今天吃多了") });
  });
});

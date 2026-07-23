import { afterEach, describe, expect, it, vi } from "vitest";
import { ACCESS_TOKEN_STORAGE_KEY, clearAccessToken, localizeBackendMessage, request, setAccessToken } from "./api";

describe("request authentication", () => {
  afterEach(() => {
    window.localStorage.clear();
    vi.unstubAllGlobals();
  });

  it("adds the stored bearer token to API requests", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    setAccessToken("demo-token");

    await request("/api/example");

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.headers).toBeInstanceOf(Headers);
    expect((init.headers as Headers).get("authorization")).toBe("Bearer demo-token");
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBe("demo-token");
  });

  it("does not replace an authorization header supplied by the caller", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    setAccessToken("stored-token");

    await request("/api/example", { headers: { Authorization: "Bearer explicit-token" } });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Headers).get("authorization")).toBe("Bearer explicit-token");
  });

  it("removes the saved access token", () => {
    setAccessToken("demo-token");
    clearAccessToken();

    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull();
  });
});


describe("API error localization", () => {
  it("translates AI provider errors into user-facing Chinese copy", () => {
    expect(localizeBackendMessage("AI provider is not configured")).toBe(
      "AI 服务尚未配置完整，请检查 AI_BASE_URL、AI_API_KEY 和 AI_MODEL。",
    );
  });

  it("explains when an API key lacks model access", () => {
    expect(localizeBackendMessage("AI provider access denied")).toBe(
      "\u5f53\u524d API Key \u6ca1\u6709\u4f7f\u7528\u8fd9\u4e2a\u6a21\u578b\u6216\u5206\u7ec4\u7684\u6743\u9650\uff0c\u8bf7\u5728\u4e2d\u8f6c\u7ad9\u6388\u6743\u540e\u91cd\u8bd5\u3002",
    );
  });

});

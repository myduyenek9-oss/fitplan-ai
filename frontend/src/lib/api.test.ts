import { afterEach, describe, expect, it, vi } from "vitest";
import { ACCESS_TOKEN_STORAGE_KEY, clearAccessToken, request, setAccessToken } from "./api";

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

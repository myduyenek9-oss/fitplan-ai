import { afterEach, describe, expect, it, vi } from "vitest";
import { getCurrentUser, login, setupAccount } from "./auth-api";

describe("auth API", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sets up the single account with JSON credentials", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: 1, username: "owner" }), {
        status: 201,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(setupAccount({ username: "owner", password: "password-123" })).resolves.toEqual({
      id: 1,
      username: "owner",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/setup",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ username: "owner", password: "password-123" }),
      }),
    );
  });

  it("logs in and reads the current account", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ access_token: "token", token_type: "bearer" }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ id: 1, username: "owner" }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(login({ username: "owner", password: "password-123" })).resolves.toMatchObject({
      access_token: "token",
    });
    await expect(getCurrentUser()).resolves.toMatchObject({ username: "owner" });

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(["/api/auth/login", "/api/auth/me"]);
  });
});

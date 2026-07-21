import { afterEach, describe, expect, it, vi } from "vitest";
import { generatePlan, getCurrentPlan } from "./plan-api";

function response(payload: unknown) {
  return new Response(JSON.stringify(payload), { status: 200, headers: { "content-type": "application/json" } });
}

describe("plan API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("fetches and generates the current plan", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(response({ id: 1 })));
    vi.stubGlobal("fetch", fetchMock);
    await getCurrentPlan();
    await generatePlan("2026-07-21");
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(["/api/plans/current", "/api/plans/generate"]);
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: "POST", body: expect.stringContaining("2026-07-21") });
  });
});

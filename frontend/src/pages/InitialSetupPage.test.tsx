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
  it("shows validation before making a calculation request", async () => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    render(<InitialSetupPage onCompleted={vi.fn()} />);
    fireEvent.click(document.querySelector('button[type="button"]') as HTMLButtonElement);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ACCESS_TOKEN_STORAGE_KEY } from "../../lib/api";
import { OnboardingForm } from "./OnboardingForm";

function response(payload: unknown, status = 200) { return new Response(JSON.stringify(payload), { status, headers: { "content-type": "application/json" } }); }

describe("OnboardingForm", () => {
  afterEach(() => { cleanup(); window.localStorage.clear(); vi.unstubAllGlobals(); });
  it("creates the account, logs in, and persists an access token", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(response({ id: 1 }, 201)).mockResolvedValueOnce(response({ access_token: "saved-token", token_type: "bearer" }));
    vi.stubGlobal("fetch", fetchMock);
    const onAuthenticated = vi.fn(); const user = userEvent.setup();
    render(<OnboardingForm onAuthenticated={onAuthenticated} />);
    await user.type(document.getElementById("auth-username") as HTMLInputElement, "owner");
    await user.type(document.getElementById("auth-password") as HTMLInputElement, "password-123");
    await user.click(document.querySelector('button[type="submit"]') as HTMLButtonElement);
    await waitFor(() => expect(onAuthenticated).toHaveBeenCalledTimes(1));
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBe("saved-token");
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(["/api/auth/setup", "/api/auth/login"]);
  });
  it("switches to login when the single account already exists", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response({ detail: "already initialized" }, 409));
    vi.stubGlobal("fetch", fetchMock);
    render(<OnboardingForm onAuthenticated={vi.fn()} />);
    fireEvent.change(document.getElementById("auth-username") as HTMLInputElement, { target: { value: "owner" } });
    fireEvent.change(document.getElementById("auth-password") as HTMLInputElement, { target: { value: "password-123" } });
    fireEvent.click(document.querySelector('button[type="submit"]') as HTMLButtonElement);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect((document.querySelector('button[type="submit"]') as HTMLButtonElement).textContent).toContain("FitPlan AI");
  });
});

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ACCESS_TOKEN_STORAGE_KEY } from "../../lib/api";
import { OnboardingForm } from "./OnboardingForm";

describe("OnboardingForm", () => {
  afterEach(() => {
    cleanup();
    window.localStorage.clear();
    vi.unstubAllGlobals();
  });

  it("creates the account, logs in, and persists the access token", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ id: 1, username: "owner" }), {
          status: 201,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ access_token: "saved-token", token_type: "bearer" }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);
    const onAuthenticated = vi.fn();
    const user = userEvent.setup();

    render(<OnboardingForm onAuthenticated={onAuthenticated} />);
    await user.type(screen.getByLabelText("???"), "owner");
    await user.type(screen.getByLabelText("??"), "password-123");
    await user.click(screen.getByRole("button", { name: "?????" }));

    await waitFor(() => expect(onAuthenticated).toHaveBeenCalledTimes(1));
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBe("saved-token");
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(["/api/auth/setup", "/api/auth/login"]);
  });

  it("switches to login after the initial account is already initialized", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "A user has already been initialized" }), {
        status: 409,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<OnboardingForm onAuthenticated={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("???"), { target: { value: "owner" } });
    fireEvent.change(screen.getByLabelText("??"), { target: { value: "password-123" } });
    fireEvent.click(screen.getByRole("button", { name: "?????" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("?????");
    expect(screen.getByRole("button", { name: "?? FitPlan AI" })).toBeInTheDocument();
  });
});

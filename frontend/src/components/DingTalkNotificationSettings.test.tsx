import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DingTalkNotificationSettings } from "./DingTalkNotificationSettings";

function response(payload: unknown) {
  return new Response(JSON.stringify(payload), { status: 200, headers: { "content-type": "application/json" } });
}

describe("DingTalkNotificationSettings", () => {
  afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

  it("loads the saved notification status when the page opens", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(response({
      is_configured: true,
      is_enabled: true,
      webhook_hint: "已绑定 · …token",
      has_signing_secret: false,
      keyword: "热量计划",
      created_at: null,
      updated_at: null,
    }));
    vi.stubGlobal("fetch", fetchMock);

    render(<DingTalkNotificationSettings />);

    expect(screen.getByText("读取中")).toBeInTheDocument();
    expect(await screen.findByText("已开启")).toBeInTheDocument();
    expect(screen.queryByText("待配置")).not.toBeInTheDocument();
    expect(screen.getByText("已绑定 · …token")).toBeInTheDocument();
  });

  it("accepts a Chinese custom keyword separately from the signing secret", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ is_configured: false, is_enabled: false, webhook_hint: null, has_signing_secret: false, keyword: null, created_at: null, updated_at: null }))
      .mockResolvedValueOnce(response({ is_configured: true, is_enabled: true, webhook_hint: "已绑定 · …token", has_signing_secret: false, keyword: "热量计划", created_at: null, updated_at: null }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<DingTalkNotificationSettings />);

    await screen.findByPlaceholderText("例如：热量计划");
    await user.type(screen.getByLabelText("Webhook 地址"), "https://oapi.dingtalk.com/robot/send?access_token=test-token");
    await user.type(screen.getByPlaceholderText("例如：热量计划"), "热量计划");
    await user.click(screen.getByRole("button", { name: "保存并开启推送" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const request = fetchMock.mock.calls[1][1] as RequestInit;
    expect(JSON.parse(String(request.body))).toMatchObject({ keyword: "热量计划", secret: null });
    expect(await screen.findByText("自定义关键词：热量计划")).toBeInTheDocument();
  });
});

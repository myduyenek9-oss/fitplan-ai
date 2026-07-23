import { useEffect, useState } from "react";
import { EditorialButton } from "./EditorialButton";
import {
  type DingTalkNotification,
  deleteDingTalkNotification,
  getDingTalkNotification,
  sendDingTalkTestPush,
  setDingTalkNotificationEnabled,
  upsertDingTalkNotification,
} from "../lib/profile-api";

function readError(error: unknown): string {
  return error instanceof Error ? error.message : "操作暂时失败，请稍后再试。";
}

const emptyNotification: DingTalkNotification = {
  is_configured: false,
  is_enabled: false,
  webhook_hint: null,
  has_signing_secret: false,
  keyword: null,
  created_at: null,
  updated_at: null,
};

export function DingTalkNotificationSettings() {
  const [notification, setNotification] = useState<DingTalkNotification | null>(null);
  const [webhook, setWebhook] = useState("");
  const [secret, setSecret] = useState("");
  const [keyword, setKeyword] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isCurrent = true;

    async function loadNotification() {
      try {
        const value = await getDingTalkNotification();
        if (!isCurrent) return;
        setNotification(value);
        setKeyword(value.keyword ?? "");
        setShowForm(!value.is_configured);
      } catch (nextError) {
        if (!isCurrent) return;
        setError("读取钉钉设置失败：" + readError(nextError));
      } finally {
        if (isCurrent) setIsLoading(false);
      }
    }

    void loadNotification();
    return () => {
      isCurrent = false;
    };
  }, []);

  async function openSettings() {
    setError(null);
    setMessage(null);
    setIsLoading(true);
    try {
      const value = await getDingTalkNotification();
      setNotification(value);
      setKeyword(value.keyword ?? "");
      setShowForm(!value.is_configured);
    } catch (nextError) {
      setError("读取钉钉设置失败：" + readError(nextError));
    } finally {
      setIsLoading(false);
    }
  }

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    if (!webhook.trim()) {
      setError("请粘贴钉钉自定义机器人的 Webhook 地址。");
      return;
    }
    setIsSaving(true);
    try {
      const value = await upsertDingTalkNotification({
        webhook: webhook.trim(),
        secret: secret.trim() || null,
        keyword: keyword.trim() || null,
        is_enabled: true,
      });
      setNotification(value);
      setWebhook("");
      setSecret("");
      setKeyword(value.keyword ?? "");
      setShowForm(false);
      setMessage("已安全保存。每天早上会只向这个钉钉机器人发送你的计划。");
    } catch (nextError) {
      setError("保存失败：" + readError(nextError));
    } finally {
      setIsSaving(false);
    }
  }

  async function toggleEnabled() {
    if (!notification) return;
    setError(null);
    setMessage(null);
    setIsSaving(true);
    try {
      const value = await setDingTalkNotificationEnabled(!notification.is_enabled);
      setNotification(value);
      setMessage(value.is_enabled ? "已恢复每日推送。" : "已暂停每日推送，机器人地址仍安全保留。");
    } catch (nextError) {
      setError("更新失败：" + readError(nextError));
    } finally {
      setIsSaving(false);
    }
  }

  async function testPush() {
    setError(null);
    setMessage(null);
    setIsTesting(true);
    try {
      await sendDingTalkTestPush();
      setMessage("测试消息已发送到你绑定的钉钉机器人。");
    } catch (nextError) {
      setError("发送失败：" + readError(nextError));
    } finally {
      setIsTesting(false);
    }
  }

  async function disconnect() {
    if (!window.confirm("确定解除这个钉钉机器人吗？之后将不再发送每日计划。")) return;
    setError(null);
    setMessage(null);
    setIsSaving(true);
    try {
      await deleteDingTalkNotification();
      setNotification(emptyNotification);
      setKeyword("");
      setShowForm(false);
      setMessage("已解除绑定，并已从数据库中删除该机器人凭据。");
    } catch (nextError) {
      setError("解除失败：" + readError(nextError));
    } finally {
      setIsSaving(false);
    }
  }

  function toggleRebindForm() {
    setKeyword(notification?.keyword ?? "");
    setShowForm((value) => !value);
  }

  const hasLoaded = notification !== null;
  const isConfigured = notification?.is_configured ?? false;

  return (
    <section className="dingtalk-settings" aria-labelledby="dingtalk-settings-title">
      <div className="dingtalk-settings__heading">
        <div><p>通知设置</p><h2 id="dingtalk-settings-title">钉钉每日计划</h2></div>
        <span className={isConfigured && notification?.is_enabled ? "dingtalk-settings__status is-on" : "dingtalk-settings__status"}>
          {isLoading ? "读取中" : !hasLoaded ? "待配置" : isConfigured && notification?.is_enabled ? "已开启" : isConfigured ? "已暂停" : "未绑定"}
        </span>
      </div>
      <p className="dingtalk-settings__intro">绑定的是你自己的钉钉自定义机器人。Webhook 与加签密钥会加密保存；中文自定义关键词会跟随你的账号保存，并自动放进每条推送内容中。</p>

      {!hasLoaded && !isLoading ? <div className="dingtalk-settings__entry"><span>每天早上把计划发到你自己的钉钉群。</span><EditorialButton type="button" variant="secondary" onClick={openSettings}>配置钉钉</EditorialButton></div> : null}
      {isLoading ? <p className="dingtalk-settings__muted">正在读取你的通知设置…</p> : null}
      {!isLoading && isConfigured ? <div className="dingtalk-settings__bound">
        <div>
          <strong>{notification?.webhook_hint}</strong>
          <span>{notification?.keyword ? `自定义关键词：${notification.keyword}` : "未使用自定义关键词"}</span>
          <span>{notification?.has_signing_secret ? "已配置加签密钥" : "未使用加签密钥"}</span>
        </div>
        <div className="dingtalk-settings__actions">
          <EditorialButton type="button" variant="secondary" onClick={toggleEnabled} disabled={isSaving}>{notification?.is_enabled ? "暂停推送" : "恢复推送"}</EditorialButton>
          <EditorialButton type="button" variant="secondary" onClick={testPush} loading={isTesting} loadingLabel="发送中…" disabled={!notification?.is_enabled || isSaving}>发送测试</EditorialButton>
          <button className="dingtalk-settings__link" type="button" onClick={toggleRebindForm}>重新绑定</button>
          <button className="dingtalk-settings__link is-danger" type="button" onClick={disconnect} disabled={isSaving}>解除绑定</button>
        </div>
      </div> : null}

      {hasLoaded && !isLoading && (!isConfigured || showForm) ? <form className="dingtalk-settings__form" onSubmit={save} noValidate>
        <p>{isConfigured ? "重新绑定时，请粘贴新的完整地址。" : "在钉钉群中添加“自定义机器人”，复制 Webhook 地址后粘贴到这里。"}</p>
        <label htmlFor="dingtalk-webhook">
          <span>Webhook 地址</span>
          <input id="dingtalk-webhook" type="url" value={webhook} onChange={(event) => setWebhook(event.target.value)} placeholder="https://oapi.dingtalk.com/robot/send?access_token=…" autoComplete="off" disabled={isSaving} />
        </label>
        <label htmlFor="dingtalk-keyword">
          <span>自定义关键词 <em>（可选，支持中文）</em></span>
          <input id="dingtalk-keyword" type="text" value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="例如：热量计划" maxLength={128} autoComplete="off" disabled={isSaving} />
          <small>钉钉机器人安全设置选择“自定义关键词”时填写，推送正文会自动包含完整关键词。</small>
        </label>
        <label htmlFor="dingtalk-secret">
          <span>加签密钥 <em>（可选）</em></span>
          <input id="dingtalk-secret" type="password" value={secret} onChange={(event) => setSecret(event.target.value)} placeholder="通常以 SEC 开头" autoComplete="new-password" disabled={isSaving} />
          <small>只有机器人启用了“加签”时才填写；如果你使用自定义关键词，这一项可以留空。</small>
        </label>
        <div className="dingtalk-settings__actions"><EditorialButton type="submit" variant="accent" loading={isSaving} loadingLabel="加密保存中…">保存并开启推送</EditorialButton>{isConfigured ? <EditorialButton type="button" variant="secondary" onClick={() => setShowForm(false)} disabled={isSaving}>取消</EditorialButton> : null}</div>
      </form> : null}
      {message ? <p className="dingtalk-settings__message" role="status">{message}</p> : null}
      {error ? <p className="dingtalk-settings__error" role="alert">{error}</p> : null}
    </section>
  );
}

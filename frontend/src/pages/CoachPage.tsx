import { useEffect, useRef, useState, type FormEvent } from "react";
import { AppShell } from "../components/AppShell";
import { EditorialButton } from "../components/EditorialButton";
import { CoachMarkdown } from "../components/CoachMarkdown";
import {
  clearChatHistory,
  deleteChatMessages,
  getChatHistory,
  sendChatMessage,
  type ChatMessage,
} from "../lib/chat-api";
import type { NavKey } from "../lib/types";

export type CoachPageProps = {
  onNavigate: (key: NavKey) => void;
};

const starterPrompts = [
  "我今天多吃了一顿火锅，晚餐怎么调整？",
  "这周有两天没时间训练，帮我重新安排。",
  "我不想吃鸡胸肉，有哪些高蛋白替代？",
];

function localDateString(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

const chatDateFormatter = new Intl.DateTimeFormat("zh-CN", {
  year: "numeric",
  month: "long",
  day: "numeric",
});
const chatTimeFormatter = new Intl.DateTimeFormat("zh-CN", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});

type SerializedDateTimeParts = {
  year: string;
  month: string;
  day: string;
  hour: string;
  minute: string;
  second: string;
};

function serializedDateTimeParts(value?: string): SerializedDateTimeParts | null {
  if (!value) return null;
  const match = value.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/);
  if (!match) return null;
  const [, year, month, day, hour, minute, second = "00"] = match;
  return { year, month, day, hour, minute, second };
}

function formatChatDate(value?: string): string {
  if (!value) return "";
  const serialized = serializedDateTimeParts(value);
  if (serialized) {
    return serialized.year + "年" + Number(serialized.month) + "月" + Number(serialized.day) + "日";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : chatDateFormatter.format(date);
}

function formatChatTime(value?: string): string {
  if (!value) return "";
  const serialized = serializedDateTimeParts(value);
  if (serialized) return serialized.hour + ":" + serialized.minute + ":" + serialized.second;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "" : chatTimeFormatter.format(date);
}

function chatError(error: unknown): string {
  return error instanceof Error ? error.message : "AI 教练暂时无法回复，请稍后再试。";
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isAssistant = message.role === "assistant";
  return (
    <article className={`coach-message coach-message--${message.role}`}>
      <img
        className="coach-message__avatar"
        src={isAssistant ? "/avatars/ai-coach-avatar.jpg" : "/avatars/user-avatar.jpg"}
        alt={isAssistant ? "AI 教练头像" : "我的头像"}
      />
      <div className="coach-message__bubble">
        <p className="coach-message__name">
          <span>{isAssistant ? "FitPlan AI 教练" : "你"}</span>
          {message.id >= 0 ? <time className="coach-message__time" dateTime={message.created_at}>{formatChatTime(message.created_at)}</time> : null}
        </p>
        {isAssistant ? <CoachMarkdown content={message.content} /> : <div className="coach-message__plain">{message.content}</div>}
        {message.recorded_food ? <div className="coach-exercise-sync" role="status"><span aria-hidden="true">✓</span><div><strong>已同步到饮食记录</strong><small>{message.recorded_food.original_text} · 约 {Math.round(message.recorded_food.calories)} kcal</small></div></div> : null}
        {message.recorded_exercise ? <div className="coach-exercise-sync" role="status"><span aria-hidden="true">✓</span><div><strong>已同步到运动记录</strong><small>{message.recorded_exercise.exercise_type} · {Math.round(message.recorded_exercise.duration_minutes)} 分钟 · 约 {Math.round(message.recorded_exercise.calories_burned)} kcal</small></div></div> : null}
        {isAssistant && message.plan_adjustment ? (
          <div className={`coach-exercise-sync coach-plan-sync coach-plan-sync--${message.plan_adjustment.status}`} role="status">
            <span aria-hidden="true">{message.plan_adjustment.status === "applied" ? "✓" : "!"}</span>
            <div>
              <strong>
                {message.plan_adjustment.status !== "applied"
                  ? "计划暂未调整"
                  : message.plan_adjustment.action === "replace_meal"
                    ? "餐食安排已更新"
                    : "训练计划已更新"}
              </strong>
              <small>
                {message.plan_adjustment.message}
                {message.plan_adjustment.status === "applied" && message.plan_adjustment.action === "replace_meal"
                  ? " 已保留其他餐次、训练和日期不变。"
                  : null}
              </small>
            </div>
          </div>
        ) : null}
      </div>
    </article>
  );
}

export function CoachPage({ onNavigate }: CoachPageProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isManagingHistory, setIsManagingHistory] = useState(false);
  const [selectedMessageIds, setSelectedMessageIds] = useState<Set<number>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const messageSequence = useRef(-1);
  const messagesRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let current = true;
    void getChatHistory()
      .then((history) => { if (current) setMessages(history); })
      .catch((nextError: unknown) => { if (current) setError(chatError(nextError)); })
      .finally(() => { if (current) setIsLoading(false); });
    return () => { current = false; };
  }, []);

  useEffect(() => {
    const container = messagesRef.current;
    if (!container) return;
    container.scrollTop = container.scrollHeight;
  }, [isLoading, messages.length, isSending]);

  function toggleMessageSelection(messageId: number) {
    if (messageId < 0) return;
    setSelectedMessageIds((current) => {
      const next = new Set(current);
      if (next.has(messageId)) next.delete(messageId);
      else next.add(messageId);
      return next;
    });
  }

  function stopManagingHistory() {
    setIsManagingHistory(false);
    setSelectedMessageIds(new Set());
  }

  async function deleteSelectedHistory() {
    const messageIds = [...selectedMessageIds];
    if (messageIds.length === 0 || isDeleting) return;
    if (!window.confirm(`确定删除选中的 ${messageIds.length} 条聊天记录吗？删除后无法恢复。`)) return;
    setIsDeleting(true);
    setError(null);
    try {
      await deleteChatMessages(messageIds);
      setMessages((current) => current.filter((message) => !selectedMessageIds.has(message.id)));
      stopManagingHistory();
    } catch (nextError) {
      setError(chatError(nextError));
    } finally {
      setIsDeleting(false);
    }
  }

  async function clearHistory() {
    if (messages.length === 0 || isDeleting) return;
    if (!window.confirm("确定一键清空全部聊天记录吗？此操作无法撤销，但不会删除你的饮食、运动、个人资料和计划。")) return;
    setIsDeleting(true);
    setError(null);
    try {
      await clearChatHistory();
      setMessages([]);
      stopManagingHistory();
    } catch (nextError) {
      setError(chatError(nextError));
    } finally {
      setIsDeleting(false);
    }
  }

  async function send(message = draft) {
    const normalized = message.trim();
    if (!normalized || isSending) return;
    const temporaryUserMessage: ChatMessage = { id: messageSequence.current--, role: "user", content: normalized, created_at: new Date().toISOString() };
    setMessages((current) => [...current, temporaryUserMessage]);
    setDraft("");
    setIsSending(true);
    setError(null);
    try {
      const result = await sendChatMessage(normalized, localDateString());
      const persistedUserMessage: ChatMessage = {
        ...temporaryUserMessage,
        id: result.user_message_id,
        created_at: result.user_created_at,
      };
      const assistantMessage: ChatMessage = {
        id: result.conversation_id,
        role: "assistant",
        content: result.reply,
        created_at: result.assistant_created_at,
        recorded_food: result.recorded_food,
        recorded_exercise: result.recorded_exercise,
        plan_adjustment: result.plan_adjustment,
      };
      setMessages((current) => [
        ...current.filter((item) => item.id !== temporaryUserMessage.id),
        persistedUserMessage,
        assistantMessage,
      ]);
    } catch (nextError) {
      setMessages((current) => current.filter((item) => item.id !== temporaryUserMessage.id));
      setError(chatError(nextError));
    } finally {
      setIsSending(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void send();
  }

  return (
    <AppShell activeNav="coach" onNavigate={onNavigate} eyebrow="AI 私教 · 会记住你的上下文" title="和 AI 调整计划" subtitle="告诉它你的实际情况：吃多了、训练赶不上、食材不喜欢，都可以重新安排。">
      <section className="coach-layout">
        <aside className="coach-guide">
          <div className="coach-guide__eyebrow">
            <span aria-hidden="true">✦</span>
            <p>今天不用重新开始</p>
          </div>
          <h2>有变化，就把计划调到你能继续执行的样子。</h2>
          <ul><li>聊天记录会保存；AI 只读取最近对话，优先参考你的资料、目标、真实记录和计划</li><li>会参考今天的热量、运动与当前 7 天计划</li><li>不提供医疗诊断，身体不适请咨询医生</li></ul>
          <EditorialButton variant="dingtalk-action" onClick={() => onNavigate("plans")}>查看 7 天计划</EditorialButton>
        </aside>
        <section className="coach-chat" aria-label="与 AI 教练交流">
          <div className="coach-chat__header">
            <div><p>你的专属教练</p><h2>FitPlan AI</h2></div>
            <div className="coach-chat__header-actions">
              {messages.length > 0 && !isManagingHistory ? (
                <>
                  <button type="button" className="coach-chat__history-action" onClick={() => setIsManagingHistory(true)} disabled={isDeleting || isSending}>选择删除</button>
                  <button type="button" className="coach-chat__history-action coach-chat__history-action--danger" onClick={() => void clearHistory()} disabled={isDeleting || isSending}>一键清空</button>
                </>
              ) : null}
              {isManagingHistory ? (
                <>
                  <small className="coach-chat__selection-count">已选 {selectedMessageIds.size} 条</small>
                  <button type="button" className="coach-chat__history-action coach-chat__history-action--danger" onClick={() => void deleteSelectedHistory()} disabled={selectedMessageIds.size === 0 || isDeleting}>{isDeleting ? "正在删除…" : "删除所选"}</button>
                  <button type="button" className="coach-chat__history-action" onClick={stopManagingHistory} disabled={isDeleting}>取消</button>
                </>
              ) : null}
              <span className="coach-chat__online">在线</span>
            </div>
          </div>
          <div ref={messagesRef} className="coach-chat__messages" aria-live="polite">
            {isLoading ? <p className="page-inline-loading">正在加载你的对话…</p> : null}
            {!isLoading && messages.length === 0 ? <div className="coach-chat__empty"><span aria-hidden="true">◎</span><p>从今天最真实的变化开始说吧。</p><small>例如：多吃了一块蛋糕、临时加班没法训练，或者想把晚餐换成外卖。</small></div> : null}
            {messages.map((message, index) => {
              const previousMessage = messages[index - 1];
              const showDate = !previousMessage || formatChatDate(previousMessage.created_at) !== formatChatDate(message.created_at);
              const selected = selectedMessageIds.has(message.id);
              return (
                <div className="coach-message-group" key={message.id}>
                  {showDate ? (
                    <div className="coach-message__date">
                      <time dateTime={message.created_at}>{formatChatDate(message.created_at)}</time>
                    </div>
                  ) : null}
                  <div className={`coach-message-item coach-message-item--${message.role}${isManagingHistory ? " coach-message-item--selecting" : ""}`}>
                    {isManagingHistory ? (
                      <label className={`coach-message__selector${selected ? " coach-message__selector--selected" : ""}`}>
                        <input type="checkbox" checked={selected} onChange={() => toggleMessageSelection(message.id)} aria-label={`选择聊天记录：${message.content.slice(0, 24)}`} />
                        <span aria-hidden="true">{selected ? "✓" : ""}</span>
                      </label>
                    ) : null}
                    <MessageBubble message={message} />
                  </div>
                </div>
              );
            })}
            {isSending ? <article className="coach-message coach-message--assistant coach-message--typing"><img className="coach-message__avatar" src="/avatars/ai-coach-avatar.jpg" alt="AI 教练头像" /><div><p>FitPlan AI 教练</p><div>正在根据你的记录调整…</div></div></article> : null}
          </div>
          {error ? <p className="coach-chat__error" role="alert">{error}</p> : null}
          <div className="coach-starters" aria-label="对话示例">{starterPrompts.map((prompt) => <button type="button" key={prompt} onClick={() => void send(prompt)} disabled={isSending || isDeleting}>{prompt}</button>)}</div>
          <form className="coach-composer" onSubmit={submit}>
            <label className="sr-only" htmlFor="coach-message">告诉 AI 教练你的变化</label>
            <textarea id="coach-message" rows={3} value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="例如：我刚吃了一份炸鸡，今天剩下的餐怎么安排？" disabled={isDeleting} />
            <EditorialButton type="submit" variant="dingtalk-action" loading={isSending} loadingLabel="正在调整…">发送给 AI</EditorialButton>
          </form>
        </section>
      </section>
    </AppShell>
  );
}

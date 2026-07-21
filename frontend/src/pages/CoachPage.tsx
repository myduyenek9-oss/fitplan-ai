import { useEffect, useRef, useState, type FormEvent } from "react";
import { AppShell } from "../components/AppShell";
import { EditorialButton } from "../components/EditorialButton";
import { getChatHistory, sendChatMessage, type ChatMessage } from "../lib/chat-api";
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

function chatError(error: unknown): string {
  return error instanceof Error ? error.message : "AI 教练暂时无法回复，请稍后再试。";
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isAssistant = message.role === "assistant";
  return <article className={`coach-message coach-message--${message.role}`}><span aria-hidden="true">{isAssistant ? "✦" : "我"}</span><div><p>{isAssistant ? "FitPlan AI 教练" : "你"}</p><div>{message.content}</div></div></article>;
}

export function CoachPage({ onNavigate }: CoachPageProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messageSequence = useRef(-1);

  useEffect(() => {
    let current = true;
    void getChatHistory()
      .then((history) => { if (current) setMessages(history); })
      .catch((nextError: unknown) => { if (current) setError(chatError(nextError)); })
      .finally(() => { if (current) setIsLoading(false); });
    return () => { current = false; };
  }, []);

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
      setMessages((current) => [...current, { id: result.conversation_id, role: "assistant", content: result.reply, created_at: new Date().toISOString() }]);
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
          <span aria-hidden="true">✦</span>
          <p>今天不用重新开始</p>
          <h2>有变化，就把计划调到你能继续执行的样子。</h2>
          <ul><li>已保存你的对话，下一次可以接着聊</li><li>会参考今天的热量、运动与当前 7 天计划</li><li>不提供医疗诊断，身体不适请咨询医生</li></ul>
          <EditorialButton variant="secondary" onClick={() => onNavigate("plans")}>查看 7 天计划</EditorialButton>
        </aside>
        <section className="coach-chat" aria-label="与 AI 教练交流">
          <div className="coach-chat__header"><div><p>你的专属教练</p><h2>FitPlan AI</h2></div><span>在线</span></div>
          <div className="coach-chat__messages" aria-live="polite">
            {isLoading ? <p className="page-inline-loading">正在加载你的对话…</p> : null}
            {!isLoading && messages.length === 0 ? <div className="coach-chat__empty"><span aria-hidden="true">◎</span><p>从今天最真实的变化开始说吧。</p><small>例如：多吃了一块蛋糕、临时加班没法训练，或者想把晚餐换成外卖。</small></div> : null}
            {messages.map((message) => <MessageBubble key={message.id} message={message} />)}
            {isSending ? <article className="coach-message coach-message--assistant coach-message--typing"><span aria-hidden="true">✦</span><div><p>FitPlan AI 教练</p><div>正在根据你的记录调整…</div></div></article> : null}
          </div>
          {error ? <p className="coach-chat__error" role="alert">{error}</p> : null}
          <div className="coach-starters" aria-label="对话示例">{starterPrompts.map((prompt) => <button type="button" key={prompt} onClick={() => void send(prompt)} disabled={isSending}>{prompt}</button>)}</div>
          <form className="coach-composer" onSubmit={submit}>
            <label className="sr-only" htmlFor="coach-message">告诉 AI 教练你的变化</label>
            <textarea id="coach-message" rows={3} value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="例如：我刚吃了一份炸鸡，今天剩下的餐怎么安排？" />
            <EditorialButton type="submit" variant="accent" loading={isSending} loadingLabel="正在调整…">发送给 AI</EditorialButton>
          </form>
        </section>
      </section>
    </AppShell>
  );
}

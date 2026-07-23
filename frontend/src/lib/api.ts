/// <reference types="vite/client" />

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
export const ACCESS_TOKEN_STORAGE_KEY = "fitplan.ai.accessToken";

export class ApiError extends Error {
  status: number;
  details: unknown;

  constructor(message: string, status: number, details: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
}

export function setAccessToken(token: string): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
}

export function clearAccessToken(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
}

async function parseResponse(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  const text = await response.text();

  if (!contentType.toLowerCase().includes("application/json")) {
    return text;
  }

  if (text.length === 0) {
    return undefined;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object";
}

function safeStringify(value: unknown): string | undefined {
  try {
    return JSON.stringify(value);
  } catch {
    return undefined;
  }
}

function formatLocation(location: unknown): string | undefined {
  if (Array.isArray(location)) {
    return location.map(String).join(".");
  }

  if (typeof location === "string") {
    return location;
  }

  return undefined;
}

function formatDetailEntry(entry: unknown): string | undefined {
  if (!isRecord(entry)) {
    return typeof entry === "string" ? entry : safeStringify(entry);
  }

  const message =
    typeof entry.msg === "string"
      ? entry.msg
      : typeof entry.message === "string"
        ? entry.message
        : undefined;

  if (message === undefined) {
    return safeStringify(entry);
  }

  const location = formatLocation(entry.loc);
  return location ? `${location}: ${message}` : message;
}

function formatDetail(detail: unknown): string | undefined {
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const entries = detail
      .map(formatDetailEntry)
      .filter((entry): entry is string => Boolean(entry));
    return entries.length > 0 ? entries.join("; ") : undefined;
  }

  if (isRecord(detail)) {
    return safeStringify(detail);
  }

  return undefined;
}

const localizedBackendMessages: Record<string, string> = {
  "AI provider is not configured": "AI 服务尚未配置完整，请检查 AI_BASE_URL、AI_API_KEY 和 AI_MODEL。",
  "AI provider timed out": "AI 服务响应超时，请稍后再试。",
  "AI provider request failed": "AI 服务请求失败，请检查 API 地址、模型名称和密钥权限。",
  "AI provider access denied": "\u5f53\u524d API Key \u6ca1\u6709\u4f7f\u7528\u8fd9\u4e2a\u6a21\u578b\u6216\u5206\u7ec4\u7684\u6743\u9650\uff0c\u8bf7\u5728\u4e2d\u8f6c\u7ad9\u6388\u6743\u540e\u91cd\u8bd5\u3002",
  "AI provider is unavailable": "暂时无法连接 AI 服务，请检查 API 地址后重试。",
  "AI provider returned invalid JSON": "AI 服务返回的数据格式不正确，请稍后再试。",
  "AI provider returned an unexpected response": "AI 服务返回了无法识别的结果，请稍后再试。",
  "AI provider returned an empty response": "AI 服务暂未返回内容，请稍后再试。",
};

export function localizeBackendMessage(message: string): string {
  return localizedBackendMessages[message] ?? message;
}

function getErrorMessage(payload: unknown, status: number): string {
  if (isRecord(payload) && "detail" in payload) {
    const formattedDetail = formatDetail(payload.detail);

    if (formattedDetail) {
      return localizeBackendMessage(formattedDetail);
    }
  }

  return `请求失败（状态码 ${status}）`;
}

function shouldSetJsonContentType(body: BodyInit | null | undefined): boolean {
  if (body === undefined || body === null) {
    return false;
  }

  return !(
    body instanceof FormData ||
    body instanceof Blob ||
    body instanceof URLSearchParams ||
    body instanceof ArrayBuffer ||
    ArrayBuffer.isView(body) ||
    body instanceof ReadableStream
  );
}

function buildHeaders(init?: RequestInit): Headers {
  const headers = new Headers(init?.headers);

  if (!headers.has("content-type") && shouldSetJsonContentType(init?.body)) {
    headers.set("Content-Type", "application/json");
  }

  const accessToken = getAccessToken();
  if (!headers.has("authorization") && accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  return headers;
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    ...init,
    headers: buildHeaders(init),
  });
  const payload = await parseResponse(response);

  if (!response.ok) {
    throw new ApiError(getErrorMessage(payload, response.status), response.status, payload);
  }

  return payload as T;
}

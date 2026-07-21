/// <reference types="vite/client" />
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

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

function getErrorMessage(payload: unknown, status: number): string {
  if (isRecord(payload) && "detail" in payload) {
    const formattedDetail = formatDetail(payload.detail);

    if (formattedDetail) {
      return formattedDetail;
    }
  }

  return `Request failed with status ${status}`;
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

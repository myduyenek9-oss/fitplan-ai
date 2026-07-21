import { request } from "./api";

export type AuthCredentials = {
  username: string;
  password: string;
};

export type AuthToken = {
  access_token: string;
  token_type: "bearer" | string;
};

export type CurrentUser = {
  id: number;
  username: string;
  created_at: string;
};

export function setupAccount(credentials: AuthCredentials): Promise<CurrentUser> {
  return request<CurrentUser>("/api/auth/setup", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

export function login(credentials: AuthCredentials): Promise<AuthToken> {
  return request<AuthToken>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

export function getCurrentUser(): Promise<CurrentUser> {
  return request<CurrentUser>("/api/auth/me");
}

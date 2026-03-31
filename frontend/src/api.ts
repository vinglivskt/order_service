import type { Order, OrderItem } from "./types";

const API = "/api";

const TOKEN_KEY = "os_token";
const USER_KEY = "os_user";

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): import("./types").SessionUser | null {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || "null");
  } catch {
    return null;
  }
}

export function saveSession(token: string, user: import("./types").SessionUser) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

/** `sub` в JWT — id пользователя (без проверки подписи, только для UI). */
export function userIdFromToken(token: string): number | null {
  try {
    let part = token.split(".")[1];
    part = part.replace(/-/g, "+").replace(/_/g, "/");
    while (part.length % 4) part += "=";
    const json = atob(part);
    const sub = JSON.parse(json) as { sub?: string };
    const id = parseInt(String(sub.sub), 10);
    return Number.isFinite(id) ? id : null;
  } catch {
    return null;
  }
}

function formatError(data: unknown, fallback: string): string {
  if (data && typeof data === "object" && "detail" in data) {
    const d = (data as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    if (d != null) return JSON.stringify(d);
  }
  return fallback;
}

export async function apiJson<T>(
  path: string,
  token: string | null,
  options: RequestInit & { skipAuth?: boolean } = {}
): Promise<T> {
  const { skipAuth, headers: h, ...rest } = options;
  const headers = new Headers(h);
  headers.set("Accept", "application/json");
  if (token && !skipAuth) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API}${path}`, { ...rest, headers });
  const text = await res.text();
  let data: unknown;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text };
  }
  if (!res.ok) {
    throw new Error(formatError(data, res.statusText || "Ошибка запроса"));
  }
  return data as T;
}

export async function loginWithPassword(
  email: string,
  password: string
): Promise<{ token: string; userId: number }> {
  const body = new URLSearchParams({ username: email, password });
  const res = await fetch(`${API}/token/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Accept: "application/json",
    },
    body,
  });
  const data = (await res.json().catch(() => ({}))) as {
    access_token?: string;
    detail?: string;
  };
  if (!res.ok) {
    throw new Error(data.detail || res.statusText);
  }
  const token = data.access_token;
  if (!token) throw new Error("Нет токена в ответе");
  const userId = userIdFromToken(token);
  if (userId == null) throw new Error("Не удалось разобрать токен");
  return { token, userId };
}

export async function registerUser(
  email: string,
  password: string
): Promise<void> {
  await apiJson<unknown>("/register/", null, {
    method: "POST",
    skipAuth: true,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export async function createOrder(
  token: string,
  items: OrderItem[]
): Promise<Order> {
  return apiJson<Order>("/orders/", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items }),
  });
}

export async function listUserOrders(
  token: string,
  userId: number
): Promise<Order[]> {
  return apiJson<Order[]>(`/orders/user/${userId}/`, token, { method: "GET" });
}

export async function getOrder(token: string, orderId: string): Promise<Order> {
  return apiJson<Order>(
    `/orders/${encodeURIComponent(orderId)}/`,
    token,
    { method: "GET" }
  );
}

export async function patchOrderStatus(
  token: string,
  orderId: string,
  status: string
): Promise<Order> {
  return apiJson<Order>(
    `/orders/${encodeURIComponent(orderId)}/`,
    token,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    }
  );
}

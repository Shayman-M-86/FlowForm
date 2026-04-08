import type { ApiError } from "./types";

const BASE_URL = "http://localhost:5000";

export class ApiRequestError extends Error {
  public readonly status: number;
  public readonly error: ApiError;

  constructor(status: number, error: ApiError) {
    super(error.message);
    this.name = "ApiRequestError";
    this.status = status;
    this.error = error;
  }
}

export interface RequestOptions {
  body?: unknown;
  headers?: HeadersInit;
}

async function request<T>(
  method: string,
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const init: RequestInit = {
    method,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  };

  if (options.body !== undefined) {
    init.body = JSON.stringify(options.body);
  }

  const res = await fetch(`${BASE_URL}${path}`, init);

  if (!res.ok) {
    let error: ApiError;
    try {
      error = (await res.json()) as ApiError;
    } catch {
      error = { code: `HTTP_${res.status}`, message: res.statusText };
    }
    throw new ApiRequestError(res.status, error);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}

export function get<T>(path: string, headers?: HeadersInit): Promise<T> {
  return request<T>("GET", path, { headers });
}

export function post<T>(
  path: string,
  body?: unknown,
  headers?: HeadersInit,
): Promise<T> {
  return request<T>("POST", path, { body, headers });
}

export function patch<T>(
  path: string,
  body: unknown,
  headers?: HeadersInit,
): Promise<T> {
  return request<T>("PATCH", path, { body, headers });
}

export function del(path: string, headers?: HeadersInit): Promise<void> {
  return request<void>("DELETE", path, { headers });
}

export function getWithQuery<T>(
  path: string,
  params: Record<string, string | number | boolean | undefined>,
  headers?: HeadersInit,
): Promise<T> {
  const q = new URLSearchParams();

  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") {
      q.set(k, String(v));
    }
  }

  const qs = q.toString();
  return get<T>(qs ? `${path}?${qs}` : path, headers);
}
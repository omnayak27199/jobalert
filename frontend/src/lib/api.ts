import type { Job, NewsItem, StateCount, Stats } from "./types";

/** Server-side calls backend directly; browser uses Next.js /api proxy. */
function getApiBase(): string {
  if (typeof window !== "undefined") {
    return process.env.NEXT_PUBLIC_API_URL || "/api";
  }
  const backend = process.env.API_URL || "http://127.0.0.1:8000";
  return `${backend.replace(/\/$/, "")}/api`;
}

async function fetchApi<T>(path: string): Promise<T> {
  const base = getApiBase();
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;
  const res = await fetch(url, {
    next: { revalidate: 60 },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} for ${url}`);
  }
  return res.json();
}

export async function getJobs(params?: {
  category?: string;
  state?: string;
  scope?: string;
  search?: string;
  closing_soon?: boolean;
  limit?: number;
}): Promise<Job[]> {
  const searchParams = new URLSearchParams();
  if (params?.category) searchParams.set("category", params.category);
  if (params?.state) searchParams.set("state", params.state);
  if (params?.scope) searchParams.set("scope", params.scope);
  if (params?.search) searchParams.set("search", params.search);
  if (params?.closing_soon) searchParams.set("closing_soon", "true");
  if (params?.limit) searchParams.set("limit", String(params.limit));
  const qs = searchParams.toString();
  return fetchApi<Job[]>(`/jobs${qs ? `?${qs}` : ""}`);
}

export async function getJob(id: number): Promise<Job> {
  const base = getApiBase();
  const url = `${base}/jobs/${id}`;
  const res = await fetch(url, { next: { revalidate: 120 } });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} for ${url}`);
  }
  return res.json();
}

export async function getNews(importantOnly = false): Promise<NewsItem[]> {
  return fetchApi<NewsItem[]>(
    `/news?important_only=${importantOnly}&limit=20`
  );
}

export async function getStats(): Promise<Stats> {
  return fetchApi<Stats>("/stats");
}

export async function getStates(): Promise<StateCount[]> {
  return fetchApi<StateCount[]>("/states");
}

export async function triggerFetch(): Promise<{ jobs: number; news: number }> {
  const base = getApiBase();
  const res = await fetch(`${base}/fetch`, { method: "POST" });
  return res.json();
}

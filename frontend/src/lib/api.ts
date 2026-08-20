import type { Job } from "./types";

/** Server-side calls backend directly; browser uses Next.js /api proxy. */
function getApiBase(): string {
  if (typeof window !== "undefined") {
    return process.env.NEXT_PUBLIC_API_URL || "/api";
  }
  const backend = process.env.API_URL || "http://127.0.0.1:8000";
  return `${backend.replace(/\/$/, "")}/api`;
}

async function fetchApi<T>(path: string, revalidateSeconds = 60): Promise<T> {
  const base = getApiBase();
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;
  const res = await fetch(url, {
    next: { revalidate: revalidateSeconds },
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
  organization?: string;
  closing_soon?: boolean;
  limit?: number;
}): Promise<Job[]> {
  const searchParams = new URLSearchParams();
  if (params?.category) searchParams.set("category", params.category);
  if (params?.state) searchParams.set("state", params.state);
  if (params?.scope) searchParams.set("scope", params.scope);
  if (params?.search) searchParams.set("search", params.search);
  if (params?.organization) searchParams.set("organization", params.organization);
  if (params?.closing_soon) searchParams.set("closing_soon", "true");
  if (params?.limit) searchParams.set("limit", String(params.limit));
  const qs = searchParams.toString();
  return fetchApi<Job[]>(`/jobs${qs ? `?${qs}` : ""}`, 60);
}

export async function getJob(id: number): Promise<Job> {
  return fetchApi<Job>(`/jobs/${id}`, 120);
}

export async function getNews(importantOnly = false): Promise<import("./types").NewsItem[]> {
  return fetchApi<import("./types").NewsItem[]>(
    `/news?important_only=${importantOnly}&limit=20`,
    120,
  );
}

export async function getStats(): Promise<import("./types").Stats> {
  return fetchApi<import("./types").Stats>("/stats", 60);
}

export async function getStates(): Promise<import("./types").StateCount[]> {
  return fetchApi<import("./types").StateCount[]>("/states", 120);
}

export interface SitemapEntry {
  id: number;
  last_modified: string | null;
}

export async function getSitemapEntries(): Promise<SitemapEntry[]> {
  return fetchApi<SitemapEntry[]>("/seo/sitemap", 3600);
}

export async function triggerFetch(): Promise<{ jobs: number; news: number }> {
  const base = getApiBase();
  const res = await fetch(`${base}/fetch`, { method: "POST", cache: "no-store" });
  return res.json();
}

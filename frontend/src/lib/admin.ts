import { getToken } from "@/lib/auth";

const ADMIN_KEY_STORAGE = "indiajob_admin_key";

export function getAdminKey(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem(ADMIN_KEY_STORAGE) || "";
}

export function saveAdminKey(key: string) {
  sessionStorage.setItem(ADMIN_KEY_STORAGE, key);
}

export function clearAdminKey() {
  sessionStorage.removeItem(ADMIN_KEY_STORAGE);
}

function headers(): Record<string, string> {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  const key = getAdminKey();
  if (key) h["X-Admin-Key"] = key;
  const token = getToken();
  if (token) h["Authorization"] = `Bearer ${token}`;
  return h;
}

function formHeaders(): Record<string, string> {
  const h: Record<string, string> = {};
  const key = getAdminKey();
  if (key) h["X-Admin-Key"] = key;
  const token = getToken();
  if (token) h["Authorization"] = `Bearer ${token}`;
  return h;
}

async function adminFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/admin${path}`, {
    ...init,
    headers: { ...headers(), ...(init?.headers as Record<string, string>) },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || data.message || "Request failed");
  }
  return data as T;
}

export interface AdminDashboard {
  total_jobs: number;
  active_jobs: number;
  inactive_jobs: number;
  today_jobs: number;
  total_users: number;
  states_covered: number;
  verified_jobs: number;
}

export interface AdminUser {
  id: number;
  email: string;
  name: string;
  phone: string | null;
  is_admin: boolean;
  created_at: string;
}

export interface AdminJob {
  id: number;
  title: string;
  organization: string;
  state: string | null;
  category: string;
  is_active: boolean;
  is_verified: boolean;
  last_date: string | null;
  created_at: string;
  source_name: string;
}

export interface AdminJobDetail {
  id: number;
  title: string;
  organization: string;
  category: string;
  scope: string;
  state: string | null;
  vacancies: number | null;
  qualification: string | null;
  description: string | null;
  full_content: string | null;
  last_date: string | null;
  exam_date: string | null;
  apply_url: string | null;
  notification_url: string | null;
  source_url: string;
  source_name: string;
  age_limit: string | null;
  application_fee: string | null;
  is_active: boolean;
  is_verified: boolean;
  published_date: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface ManualJobInput {
  title: string;
  organization: string;
  category?: string;
  scope?: string;
  state?: string;
  vacancies?: number;
  qualification?: string;
  description?: string;
  full_content?: string;
  last_date?: string;
  exam_date?: string;
  apply_url?: string;
  notification_url?: string;
  age_limit?: string;
  application_fee?: string;
  is_active?: boolean;
  is_verified?: boolean;
  send_alerts?: boolean;
}

export function fetchDashboard() {
  return adminFetch<AdminDashboard>("/dashboard");
}

export function fetchAdminUsers(q?: string) {
  const params = new URLSearchParams({ limit: "200" });
  if (q) params.set("q", q);
  return adminFetch<{ total: number; users: AdminUser[] }>(`/users?${params}`);
}

export function deleteAdminUser(id: number) {
  return adminFetch<{ status: string; user_id: number }>(`/users/${id}`, {
    method: "DELETE",
  });
}

export function fetchAdminJobs(q?: string, active?: boolean) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (active !== undefined) params.set("active", String(active));
  return adminFetch<{ total: number; jobs: AdminJob[] }>(`/jobs?${params}`);
}

export function fetchAdminJob(id: number) {
  return adminFetch<AdminJobDetail>(`/jobs/${id}`);
}

export function createManualJob(body: ManualJobInput) {
  return adminFetch<{ job_id: number; alerts: Record<string, number> }>("/jobs", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateJob(id: number, body: Partial<ManualJobInput>) {
  return adminFetch(`/jobs/${id}`, { method: "PATCH", body: JSON.stringify(body) });
}

export function deactivateJob(id: number) {
  return adminFetch(`/jobs/${id}`, { method: "DELETE" });
}

export function activateJob(id: number) {
  return adminFetch(`/jobs/${id}/activate`, { method: "POST" });
}

export function reEnrichJob(id: number) {
  return adminFetch(`/jobs/${id}/re-enrich`, { method: "POST" });
}

export function dispatchJobAlerts(id: number) {
  return adminFetch<Record<string, number>>(`/jobs/${id}/dispatch-alerts`, { method: "POST" });
}

export function triggerFetch() {
  return adminFetch<{ jobs: number; new_jobs: number; news: number }>("/fetch", { method: "POST" });
}

export function triggerCleanup() {
  return adminFetch<Record<string, number>>("/cleanup", { method: "POST" });
}

export function triggerRepair() {
  return adminFetch<{ updated: number; total: number }>("/repair", { method: "POST" });
}

export function triggerEnrichAll(force = true) {
  return adminFetch<{ enriched: number; skipped: number; errors: number; total: number }>(
    `/enrich-all?force=${force}`,
    { method: "POST" },
  );
}

export async function uploadPdf(form: FormData) {
  const res = await fetch("/api/admin/upload-pdf", {
    method: "POST",
    headers: formHeaders(),
    body: form,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Upload failed");
  return data;
}

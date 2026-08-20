const ADMIN_KEY_STORAGE = "indiajob_admin_key";

export function getAdminKey(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem(ADMIN_KEY_STORAGE) || "";
}

export function saveAdminKey(key: string) {
  sessionStorage.setItem(ADMIN_KEY_STORAGE, key);
}

function headers(): Record<string, string> {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  const key = getAdminKey();
  if (key) h["X-Admin-Key"] = key;
  return h;
}

function formHeaders(): Record<string, string> {
  const h: Record<string, string> = {};
  const key = getAdminKey();
  if (key) h["X-Admin-Key"] = key;
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

export interface ManualJobInput {
  title: string;
  organization: string;
  category?: string;
  scope?: string;
  state?: string;
  vacancies?: number;
  qualification?: string;
  description?: string;
  last_date?: string;
  exam_date?: string;
  apply_url?: string;
  notification_url?: string;
  age_limit?: string;
  application_fee?: string;
  send_alerts?: boolean;
}

export function fetchDashboard() {
  return adminFetch<AdminDashboard>("/dashboard");
}

export function fetchAdminJobs(q?: string, active?: boolean) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (active !== undefined) params.set("active", String(active));
  return adminFetch<{ total: number; jobs: AdminJob[] }>(`/jobs?${params}`);
}

export function createManualJob(body: ManualJobInput) {
  return adminFetch<{ job_id: number; alerts: Record<string, number> }>("/jobs", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateJob(id: number, body: Partial<ManualJobInput & { is_active?: boolean; is_verified?: boolean }>) {
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

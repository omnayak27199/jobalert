export interface User {
  id: number;
  email: string;
  name: string;
  phone: string | null;
  is_admin?: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface UserPreferences {
  states: string[];
  categories: string[];
  qualifications: string[];
  organizations: string[];
  email_alerts: boolean;
  whatsapp_alerts: boolean;
  alert_frequency: string;
}

export interface EducationEntry {
  degree: string;
  stream?: string;
  board_university?: string;
  year?: number;
  percentage?: string;
}

export interface ExperienceEntry {
  role: string;
  organization?: string;
  years?: number;
  domain?: string;
}

export interface ProfileStats {
  completeness_percent: number;
  education_entries: number;
  experience_entries: number;
  experience_years?: number;
  highest_qualification?: string;
  current_state?: string;
  profile_complete: boolean;
}

export interface UserProfile {
  date_of_birth?: string | null;
  gender?: string | null;
  category?: string | null;
  current_state?: string | null;
  highest_qualification?: string | null;
  education: EducationEntry[];
  experience_years?: number | null;
  experience: ExperienceEntry[];
  skills: string[];
  preferred_posts: string[];
  preferred_departments: string[];
  bio?: string | null;
  profile_complete: boolean;
  stats: ProfileStats;
}

export interface MatchedJob {
  job: import("./types").Job;
  match_score: number;
  match_reasons: string[];
}

const TOKEN_KEY = "indiajob_token";
const USER_KEY = "indiajob_user";
const LEGACY_TOKEN_KEY = "jobalert_token";
const LEGACY_USER_KEY = "jobalert_user";

function migrateLegacyAuthKeys() {
  if (typeof window === "undefined") return;
  const legacyToken = localStorage.getItem(LEGACY_TOKEN_KEY);
  const legacyUser = localStorage.getItem(LEGACY_USER_KEY);
  if (legacyToken && !localStorage.getItem(TOKEN_KEY)) {
    localStorage.setItem(TOKEN_KEY, legacyToken);
  }
  if (legacyUser && !localStorage.getItem(USER_KEY)) {
    localStorage.setItem(USER_KEY, legacyUser);
  }
  if (legacyToken) localStorage.removeItem(LEGACY_TOKEN_KEY);
  if (legacyUser) localStorage.removeItem(LEGACY_USER_KEY);
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  migrateLegacyAuthKeys();
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): User | null {
  if (typeof window === "undefined") return null;
  migrateLegacyAuthKeys();
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function saveAuth(token: string, user: User) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

function formatApiError(body: unknown, status: number): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (item && typeof item === "object" && "msg" in item) {
            return String((item as { msg: string }).msg);
          }
          return JSON.stringify(item);
        })
        .join("; ");
    }
  }
  return `HTTP ${status}`;
}

async function authFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`/api${path}`, { ...options, headers });
  if (!res.ok) {
    const text = await res.text();
    let body: unknown = { detail: "Request failed" };
    try {
      body = text ? JSON.parse(text) : body;
    } catch {
      body = { detail: text?.slice(0, 200) || `HTTP ${res.status}` };
    }
    throw new Error(formatApiError(body, res.status));
  }
  return res.json();
}

export async function register(data: {
  email: string;
  password: string;
  name: string;
  phone?: string;
}): Promise<AuthResponse> {
  return authFetch<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function login(
  email: string,
  password: string
): Promise<AuthResponse> {
  return authFetch<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function adminLogin(
  email: string,
  password: string
): Promise<AuthResponse> {
  return authFetch<AuthResponse>("/auth/admin-login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function getMe(): Promise<User> {
  return authFetch<User>("/auth/me");
}

export async function getPreferences(): Promise<UserPreferences> {
  return authFetch<UserPreferences>("/users/preferences");
}

export async function updatePreferences(
  prefs: UserPreferences
): Promise<UserPreferences> {
  return authFetch<UserPreferences>("/users/preferences", {
    method: "PUT",
    body: JSON.stringify(prefs),
  });
}

export async function getFavorites() {
  return authFetch<
    Array<{ job_id: number; created_at: string; job: import("./types").Job }>
  >("/users/favorites");
}

export async function addFavorite(jobId: number) {
  return authFetch<{ status: string }>(`/users/favorites/${jobId}`, {
    method: "POST",
  });
}

export async function removeFavorite(jobId: number) {
  return authFetch<{ status: string }>(`/users/favorites/${jobId}`, {
    method: "DELETE",
  });
}

export async function checkFavorite(jobId: number) {
  return authFetch<{ saved: boolean }>(`/users/favorites/check/${jobId}`);
}

export async function getProfile(): Promise<UserProfile> {
  return authFetch<UserProfile>("/users/profile");
}

export async function updateProfile(profile: Partial<UserProfile>): Promise<UserProfile> {
  return authFetch<UserProfile>("/users/profile", {
    method: "PUT",
    body: JSON.stringify(profile),
  });
}

export async function updateMe(data: { name?: string; phone?: string }): Promise<User> {
  return authFetch<User>("/users/me", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function getMatchedJobs(limit = 20): Promise<{
  jobs: MatchedJob[];
  profile_complete: boolean;
}> {
  return authFetch(`/users/matched-jobs?limit=${limit}`);
}

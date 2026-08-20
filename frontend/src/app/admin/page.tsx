"use client";

import {
  Bell,
  FileUp,
  LayoutDashboard,
  List,
  LogOut,
  Pencil,
  PlusCircle,
  RefreshCw,
  Settings,
  Trash2,
  Upload,
  Users,
  Wrench,
  X,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import {
  activateJob,
  clearAdminKey,
  createManualJob,
  deactivateJob,
  dispatchJobAlerts,
  fetchAdminJob,
  fetchAdminJobs,
  fetchAdminUsers,
  fetchDashboard,
  getAdminKey,
  reEnrichJob,
  saveAdminKey,
  triggerCleanup,
  triggerEnrichAll,
  triggerFetch,
  triggerRepair,
  updateJob,
  uploadPdf,
  type AdminDashboard,
  type AdminJob,
  type AdminJobDetail,
  type AdminUser,
} from "@/lib/admin";
import { adminLogin, saveAuth } from "@/lib/auth";
import { CATEGORY_LABELS, INDIAN_STATES, type JobCategory } from "@/lib/types";

type Tab = "dashboard" | "users" | "create" | "upload" | "jobs" | "system";

const TABS: { id: Tab; label: string; icon: typeof LayoutDashboard }[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "users", label: "Users", icon: Users },
  { id: "create", label: "Create Alert", icon: PlusCircle },
  { id: "upload", label: "Upload PDF", icon: FileUp },
  { id: "jobs", label: "Manage Jobs", icon: List },
  { id: "system", label: "System", icon: Settings },
];

const EMPTY_FORM = {
  title: "",
  organization: "",
  state: "",
  category: "notification",
  scope: "state",
  vacancies: "",
  qualification: "",
  description: "",
  full_content: "",
  last_date: "",
  exam_date: "",
  apply_url: "",
  notification_url: "",
  age_limit: "",
  application_fee: "",
  is_active: true,
  is_verified: true,
  send_alerts: true,
};

function toEditDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const day = String(d.getUTCDate()).padStart(2, "0");
  const month = String(d.getUTCMonth() + 1).padStart(2, "0");
  const year = d.getUTCFullYear();
  return `${day}/${month}/${year}`;
}

function jobToEditForm(job: AdminJobDetail) {
  return {
    title: job.title,
    organization: job.organization,
    state: job.state || "",
    category: job.category,
    scope: job.scope,
    vacancies: job.vacancies != null ? String(job.vacancies) : "",
    qualification: job.qualification || "",
    description: job.description || "",
    full_content: job.full_content || "",
    last_date: toEditDate(job.last_date),
    exam_date: toEditDate(job.exam_date),
    apply_url: job.apply_url || "",
    notification_url: job.notification_url || "",
    age_limit: job.age_limit || "",
    application_fee: job.application_fee || "",
    is_active: job.is_active,
    is_verified: job.is_verified,
    send_alerts: false,
  };
}

export default function AdminPage() {
  const { user, refreshUser } = useAuth();
  const [tab, setTab] = useState<Tab>("dashboard");
  const [adminKey, setAdminKey] = useState("");
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [showKeyLogin, setShowKeyLogin] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [dashboard, setDashboard] = useState<AdminDashboard | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [userSearch, setUserSearch] = useState("");
  const [jobs, setJobs] = useState<AdminJob[]>([]);
  const [jobSearch, setJobSearch] = useState("");
  const [form, setForm] = useState(EMPTY_FORM);
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [pdfMeta, setPdfMeta] = useState({ state: "", organization: "", title: "", apply_url: "", notification_url: "", send_alerts: true });
  const [editingJob, setEditingJob] = useState<AdminJobDetail | null>(null);
  const [editForm, setEditForm] = useState(EMPTY_FORM);

  const clearStatus = () => {
    setMessage(null);
    setError(null);
  };

  const run = async (fn: () => Promise<void>) => {
    clearStatus();
    setLoading(true);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Operation failed");
    } finally {
      setLoading(false);
    }
  };

  const loadDashboard = useCallback(async () => {
    const data = await fetchDashboard();
    setDashboard(data);
  }, []);

  const loadUsers = useCallback(async (q?: string) => {
    const data = await fetchAdminUsers(q);
    setUsers(data.users);
  }, []);

  const loadJobs = useCallback(async (q?: string) => {
    const data = await fetchAdminJobs(q);
    setJobs(data.jobs);
  }, []);

  useEffect(() => {
    if (user?.is_admin) {
      setAuthenticated(true);
      return;
    }
    const saved = getAdminKey();
    if (!saved) return;
    setAdminKey(saved);
    fetchDashboard()
      .then(() => setAuthenticated(true))
      .catch(() => {
        clearAdminKey();
        setAuthenticated(false);
      });
  }, [user]);

  useEffect(() => {
    if (!authenticated) return;
    if (tab === "dashboard") loadDashboard().catch((e) => setError(String(e)));
    if (tab === "users") loadUsers(userSearch).catch((e) => setError(String(e)));
    if (tab === "jobs") loadJobs(jobSearch).catch((e) => setError(String(e)));
  }, [authenticated, tab, loadDashboard, loadUsers, loadJobs, jobSearch, userSearch]);

  const handleAdminLogin = async () => {
    clearStatus();
    if (!loginEmail.trim() || !loginPassword) {
      setError("Enter admin email and password");
      return;
    }
    setLoading(true);
    try {
      const res = await adminLogin(loginEmail.trim(), loginPassword);
      saveAuth(res.access_token, res.user);
      await refreshUser();
      setAuthenticated(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Admin login failed");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyLogin = async () => {
    clearStatus();
    if (!adminKey.trim()) {
      setError("Enter your admin key from backend/.env (ADMIN_SECRET)");
      return;
    }
    saveAdminKey(adminKey.trim());
    setLoading(true);
    try {
      await fetchDashboard();
      setAuthenticated(true);
    } catch (e) {
      clearAdminKey();
      setError(e instanceof Error ? e.message : "Invalid admin key");
    } finally {
      setLoading(false);
    }
  };

  const handleAdminLogout = () => {
    clearAdminKey();
    setAuthenticated(false);
    setEditingJob(null);
    clearStatus();
  };

  const openEditJob = (jobId: number) =>
    run(async () => {
      const job = await fetchAdminJob(jobId);
      setEditingJob(job);
      setEditForm(jobToEditForm(job));
    });

  const handleSaveEdit = () =>
    run(async () => {
      if (!editingJob) return;
      await updateJob(editingJob.id, {
        title: editForm.title,
        organization: editForm.organization,
        category: editForm.category,
        scope: editForm.scope,
        state: editForm.state || undefined,
        vacancies: editForm.vacancies ? Number(editForm.vacancies) : undefined,
        qualification: editForm.qualification || undefined,
        description: editForm.description || undefined,
        full_content: editForm.full_content || undefined,
        last_date: editForm.last_date || undefined,
        exam_date: editForm.exam_date || undefined,
        apply_url: editForm.apply_url || undefined,
        notification_url: editForm.notification_url || undefined,
        age_limit: editForm.age_limit || undefined,
        application_fee: editForm.application_fee || undefined,
        is_active: editForm.is_active,
        is_verified: editForm.is_verified,
      });
      setMessage(`Job #${editingJob.id} updated`);
      setEditingJob(null);
      await loadJobs(jobSearch);
      await loadDashboard();
    });

  const handleCreate = () =>
    run(async () => {
      const res = await createManualJob({
        title: form.title,
        organization: form.organization,
        category: form.category,
        scope: form.scope,
        state: form.state || undefined,
        vacancies: form.vacancies ? Number(form.vacancies) : undefined,
        qualification: form.qualification || undefined,
        description: form.description || undefined,
        last_date: form.last_date || undefined,
        exam_date: form.exam_date || undefined,
        apply_url: form.apply_url || undefined,
        notification_url: form.notification_url || undefined,
        age_limit: form.age_limit || undefined,
        application_fee: form.application_fee || undefined,
        send_alerts: form.send_alerts,
      });
      setMessage(`Created job #${res.job_id}. Alerts: email ${res.alerts?.email_sent ?? 0}, WhatsApp ${res.alerts?.whatsapp_sent ?? 0}`);
      setForm(EMPTY_FORM);
      await loadDashboard();
    });

  const handleUpload = () =>
    run(async () => {
      if (!pdfFile) return;
      const fd = new FormData();
      fd.append("file", pdfFile);
      if (pdfMeta.state) fd.append("state", pdfMeta.state);
      if (pdfMeta.organization) fd.append("organization", pdfMeta.organization);
      if (pdfMeta.title) fd.append("title", pdfMeta.title);
      if (pdfMeta.apply_url) fd.append("apply_url", pdfMeta.apply_url);
      if (pdfMeta.notification_url) fd.append("notification_url", pdfMeta.notification_url);
      fd.append("send_alerts", String(pdfMeta.send_alerts));
      const res = await uploadPdf(fd);
      setMessage(`Published job #${res.job_id}: ${res.title}`);
      setPdfFile(null);
      await loadDashboard();
    });

  if (!authenticated) {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-md flex-col justify-center px-4">
        <h1 className="text-2xl font-bold text-slate-900">IndiaGovJob Admin</h1>
        <p className="mt-1 text-sm text-slate-500">Sign in with your admin account to manage jobs</p>

        <div className="mt-6 space-y-3">
          <input
            type="email"
            value={loginEmail}
            onChange={(e) => setLoginEmail(e.target.value)}
            placeholder="Admin email"
            className="w-full rounded-lg border border-slate-200 px-4 py-3 text-sm"
          />
          <input
            type="password"
            value={loginPassword}
            onChange={(e) => setLoginPassword(e.target.value)}
            placeholder="Password"
            className="w-full rounded-lg border border-slate-200 px-4 py-3 text-sm"
          />
          <button
            type="button"
            onClick={handleAdminLogin}
            disabled={loading}
            className="w-full rounded-lg bg-sky-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-sky-800 disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Sign in as Admin"}
          </button>
        </div>

        <button
          type="button"
          onClick={() => setShowKeyLogin(!showKeyLogin)}
          className="mt-4 text-sm text-slate-500 hover:text-sky-700"
        >
          {showKeyLogin ? "Hide admin key login" : "Use admin key instead"}
        </button>

        {showKeyLogin && (
          <div className="mt-3 space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
            <input
              type="password"
              value={adminKey}
              onChange={(e) => setAdminKey(e.target.value)}
              placeholder="ADMIN_SECRET from server .env"
              className="w-full rounded-lg border border-slate-200 px-4 py-3 text-sm"
            />
            <button
              type="button"
              onClick={handleKeyLogin}
              disabled={loading}
              className="w-full rounded-lg border border-sky-700 px-4 py-2.5 text-sm font-semibold text-sky-700 hover:bg-sky-50 disabled:opacity-50"
            >
              Enter with Admin Key
            </button>
          </div>
        )}

        {error && (
          <div className="mt-3 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        )}

        <p className="mt-6 text-xs text-slate-400">
          Admin access is limited to accounts listed in ADMIN_EMAILS on the server. Normal users cannot see this panel.
        </p>
        <p className="mt-3 text-center text-sm text-slate-500">
          <Link href="/login" className="font-medium text-sky-700 hover:underline">
            ← Back to user sign in
          </Link>
          {" · "}
          <Link href="/register" className="font-medium text-sky-700 hover:underline">
            Create account
          </Link>
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">IndiaGovJob Admin Panel</h1>
          <p className="mt-1 text-sm text-slate-500">
            Upload notifications, create alerts manually, and control the portal
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {user?.is_admin && (
            <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-900">
              {user.email}
            </span>
          )}
          <button
            type="button"
            onClick={handleAdminLogout}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
          >
            <LogOut className="h-4 w-4" />
            Exit admin
          </button>
          <Link href="/" className="text-sm font-medium text-sky-700 hover:underline">
            ← Back to site
          </Link>
        </div>
      </div>

      <nav className="mt-6 flex flex-wrap gap-2 border-b border-slate-200 pb-3">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => { setTab(id); clearStatus(); }}
            className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition ${
              tab === id ? "bg-sky-700 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </nav>

      {(error || message) && (
        <div className={`mt-4 rounded-lg px-4 py-3 text-sm ${error ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-800"}`}>
          {error || message}
        </div>
      )}

      {tab === "dashboard" && dashboard && (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Total Jobs", dashboard.total_jobs],
            ["Active", dashboard.active_jobs],
            ["Today Added", dashboard.today_jobs],
            ["Registered Users", dashboard.total_users],
            ["States", dashboard.states_covered],
            ["Verified", dashboard.verified_jobs],
            ["Inactive", dashboard.inactive_jobs],
          ].map(([label, val]) => (
            <div key={String(label)} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
              <p className="mt-1 text-2xl font-bold text-slate-900">{val}</p>
            </div>
          ))}
        </div>
      )}

      {tab === "users" && (
        <div className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-bold text-slate-900">Registered Users ({users.length})</h2>
            <input
              type="search"
              placeholder="Search email, name, phone..."
              value={userSearch}
              onChange={(e) => setUserSearch(e.target.value)}
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase text-slate-500">
                  <th className="py-2 pr-4">ID</th>
                  <th className="py-2 pr-4">Name</th>
                  <th className="py-2 pr-4">Email</th>
                  <th className="py-2 pr-4">Phone</th>
                  <th className="py-2">Joined</th>
                </tr>
              </thead>
              <tbody>
                {users.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-slate-500">
                      No users found. Check admin key or wait for registrations.
                    </td>
                  </tr>
                ) : (
                  users.map((user) => (
                    <tr key={user.id} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-mono text-xs">{user.id}</td>
                      <td className="py-2 pr-4">{user.name}</td>
                      <td className="py-2 pr-4">{user.email}</td>
                      <td className="py-2 pr-4">{user.phone || "—"}</td>
                      <td className="py-2 text-slate-500">
                        {new Date(user.created_at).toLocaleDateString("en-IN")}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "create" && (
        <form
          className="mt-6 space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
          onSubmit={(e) => { e.preventDefault(); handleCreate(); }}
        >
          <h2 className="text-lg font-bold text-slate-900">Create Job Alert Manually</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Official Title *" value={form.title} onChange={(v) => setForm({ ...form, title: v })} required />
            <Field label="Organization *" value={form.organization} onChange={(v) => setForm({ ...form, organization: v })} required />
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">State</label>
              <select value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm">
                <option value="">All India / Central</option>
                {INDIAN_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Category</label>
              <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm">
                {(Object.keys(CATEGORY_LABELS) as JobCategory[]).map((c) => (
                  <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>
                ))}
              </select>
            </div>
            <Field label="Vacancies" value={form.vacancies} onChange={(v) => setForm({ ...form, vacancies: v })} type="number" />
            <Field label="Qualification" value={form.qualification} onChange={(v) => setForm({ ...form, qualification: v })} />
            <Field label="Last Date (DD/MM/YYYY)" value={form.last_date} onChange={(v) => setForm({ ...form, last_date: v })} />
            <Field label="Exam Date" value={form.exam_date} onChange={(v) => setForm({ ...form, exam_date: v })} />
            <Field label="Apply URL" value={form.apply_url} onChange={(v) => setForm({ ...form, apply_url: v })} />
            <Field label="Notification PDF URL" value={form.notification_url} onChange={(v) => setForm({ ...form, notification_url: v })} />
            <Field label="Age Limit" value={form.age_limit} onChange={(v) => setForm({ ...form, age_limit: v })} />
            <Field label="Application Fee" value={form.application_fee} onChange={(v) => setForm({ ...form, application_fee: v })} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Description / Overview</label>
            <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={form.send_alerts} onChange={(e) => setForm({ ...form, send_alerts: e.target.checked })} />
            Send personalized alerts to matching candidates
          </label>
          <button type="submit" disabled={loading} className="rounded-lg bg-emerald-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50">
            {loading ? "Publishing..." : "Publish Alert"}
          </button>
        </form>
      )}

      {tab === "upload" && (
        <div className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-bold text-slate-900">Upload PDF Notification</h2>
          <p className="mt-1 text-sm text-slate-500">Auto-parses title, dates, eligibility from official PDF</p>
          <div className="mt-4 space-y-4">
            <input type="file" accept=".pdf" onChange={(e) => setPdfFile(e.target.files?.[0] || null)} className="w-full text-sm" />
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Title override" value={pdfMeta.title} onChange={(v) => setPdfMeta({ ...pdfMeta, title: v })} />
              <Field label="Organization override" value={pdfMeta.organization} onChange={(v) => setPdfMeta({ ...pdfMeta, organization: v })} />
              <Field label="State override" value={pdfMeta.state} onChange={(v) => setPdfMeta({ ...pdfMeta, state: v })} />
              <Field label="Apply URL" value={pdfMeta.apply_url} onChange={(v) => setPdfMeta({ ...pdfMeta, apply_url: v })} />
              <Field label="Notification URL" value={pdfMeta.notification_url} onChange={(v) => setPdfMeta({ ...pdfMeta, notification_url: v })} />
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={pdfMeta.send_alerts} onChange={(e) => setPdfMeta({ ...pdfMeta, send_alerts: e.target.checked })} />
              Send alerts after publish
            </label>
            <button type="button" disabled={loading || !pdfFile} onClick={handleUpload} className="inline-flex items-center gap-2 rounded-lg bg-sky-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-sky-800 disabled:opacity-50">
              <Upload className="h-4 w-4" />
              {loading ? "Parsing..." : "Upload & Publish"}
            </button>
          </div>
        </div>
      )}

      {tab === "jobs" && (
        <div className="mt-6 space-y-4">
          <div className="flex gap-2">
            <input
              value={jobSearch}
              onChange={(e) => setJobSearch(e.target.value)}
              placeholder="Search title, org, state..."
              className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
            <button type="button" onClick={() => loadJobs(jobSearch)} className="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium hover:bg-slate-200">
              Search
            </button>
          </div>
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="w-full min-w-[800px] text-sm">
              <thead>
                <tr className="border-b bg-slate-50 text-left text-xs uppercase text-slate-500">
                  <th className="px-3 py-2">ID</th>
                  <th className="px-3 py-2">Title</th>
                  <th className="px-3 py-2">Org</th>
                  <th className="px-3 py-2">State</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id} className="border-b border-slate-100">
                    <td className="px-3 py-2">{job.id}</td>
                    <td className="max-w-xs truncate px-3 py-2 font-medium">{job.title}</td>
                    <td className="px-3 py-2">{job.organization}</td>
                    <td className="px-3 py-2">{job.state || "—"}</td>
                    <td className="px-3 py-2">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${job.is_active ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"}`}>
                        {job.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-1">
                        <Link href={`/job/${job.id}`} target="_blank" className="rounded bg-sky-50 px-2 py-1 text-xs text-sky-800 hover:bg-sky-100">View</Link>
                        <ActionBtn label="Edit" icon={Pencil} onClick={() => openEditJob(job.id)} />
                        <ActionBtn label="Alert" icon={Bell} onClick={() => run(async () => {
                          const r = await dispatchJobAlerts(job.id);
                          setMessage(`Alerts sent — email: ${r.email_sent ?? 0}, WhatsApp: ${r.whatsapp_sent ?? 0}`);
                        })} />
                        <ActionBtn label="Enrich" icon={Wrench} onClick={() => run(async () => {
                          await reEnrichJob(job.id);
                          setMessage(`Job #${job.id} re-enriched from PDF/portal`);
                        })} />
                        {job.is_active ? (
                          <ActionBtn label="Hide" icon={Trash2} onClick={() => run(async () => {
                            await deactivateJob(job.id);
                            await loadJobs(jobSearch);
                            setMessage(`Job #${job.id} deactivated`);
                          })} />
                        ) : (
                          <ActionBtn label="Show" icon={RefreshCw} onClick={() => run(async () => {
                            await activateJob(job.id);
                            await loadJobs(jobSearch);
                            setMessage(`Job #${job.id} activated`);
                          })} />
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "system" && (
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <SystemCard
            title="Fetch All Portals"
            desc="Pull latest jobs from 58 official government & PSU sites"
            loading={loading}
            onClick={() => run(async () => {
              const r = await triggerFetch();
              setMessage(`Fetched ${r.jobs} jobs (${r.new_jobs} new). News: ${r.news}`);
              await loadDashboard();
            })}
            icon={RefreshCw}
          />
          <SystemCard
            title="Run Cleanup"
            desc="Remove junk listings, expire old jobs, rebuild sections"
            loading={loading}
            onClick={() => run(async () => {
              const r = await triggerCleanup();
              setMessage(`Cleanup done — deactivated ${r.deactivated} junk, ${r.expired} expired`);
            })}
            icon={Wrench}
          />
          <SystemCard
            title="Repair & Re-enrich"
            desc="Re-fetch official PDFs and update job detail sections"
            loading={loading}
            onClick={() => run(async () => {
              const r = await triggerRepair();
              setMessage(`Repaired ${r.updated} / ${r.total} jobs`);
            })}
            icon={Wrench}
          />
          <SystemCard
            title="Enrich All Jobs"
            desc="Deep-parse every active job PDF/portal and rebuild full advertisement sections"
            loading={loading}
            onClick={() => run(async () => {
              const r = await triggerEnrichAll(true);
              setMessage(
                `Enriched ${r.enriched}, skipped ${r.skipped}, errors ${r.errors} / ${r.total} jobs`,
              );
            })}
            icon={RefreshCw}
          />
        </div>
      )}

      {editingJob && (
        <JobEditModal
          job={editingJob}
          form={editForm}
          loading={loading}
          onChange={setEditForm}
          onClose={() => setEditingJob(null)}
          onSave={handleSaveEdit}
        />
      )}
    </div>
  );
}

function JobEditModal({
  job,
  form,
  loading,
  onChange,
  onClose,
  onSave,
}: {
  job: AdminJobDetail;
  form: typeof EMPTY_FORM;
  loading: boolean;
  onChange: (form: typeof EMPTY_FORM) => void;
  onClose: () => void;
  onSave: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 pt-10">
      <div className="w-full max-w-3xl rounded-xl border border-slate-200 bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Edit Job #{job.id}</h2>
            <p className="text-xs text-slate-500">{job.source_name} · {job.source_url}</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100">
            <X className="h-5 w-5" />
          </button>
        </div>
        <form
          className="max-h-[70vh] space-y-4 overflow-y-auto p-6"
          onSubmit={(e) => { e.preventDefault(); onSave(); }}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Title *" value={form.title} onChange={(v) => onChange({ ...form, title: v })} required />
            <Field label="Organization *" value={form.organization} onChange={(v) => onChange({ ...form, organization: v })} required />
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">State</label>
              <select value={form.state} onChange={(e) => onChange({ ...form, state: e.target.value })} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm">
                <option value="">All India / Central</option>
                {INDIAN_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Category</label>
              <select value={form.category} onChange={(e) => onChange({ ...form, category: e.target.value })} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm">
                {(Object.keys(CATEGORY_LABELS) as JobCategory[]).map((c) => (
                  <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Scope</label>
              <select value={form.scope} onChange={(e) => onChange({ ...form, scope: e.target.value })} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm">
                <option value="all_india">All India</option>
                <option value="central">Central</option>
                <option value="state">State</option>
              </select>
            </div>
            <Field label="Vacancies" value={form.vacancies} onChange={(v) => onChange({ ...form, vacancies: v })} type="number" />
            <Field label="Qualification" value={form.qualification} onChange={(v) => onChange({ ...form, qualification: v })} />
            <Field label="Last Date (DD/MM/YYYY)" value={form.last_date} onChange={(v) => onChange({ ...form, last_date: v })} />
            <Field label="Exam Date" value={form.exam_date} onChange={(v) => onChange({ ...form, exam_date: v })} />
            <Field label="Apply URL" value={form.apply_url} onChange={(v) => onChange({ ...form, apply_url: v })} />
            <Field label="Notification PDF URL" value={form.notification_url} onChange={(v) => onChange({ ...form, notification_url: v })} />
            <Field label="Age Limit" value={form.age_limit} onChange={(v) => onChange({ ...form, age_limit: v })} />
            <Field label="Application Fee" value={form.application_fee} onChange={(v) => onChange({ ...form, application_fee: v })} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Description / Overview</label>
            <textarea value={form.description} onChange={(e) => onChange({ ...form, description: e.target.value })} rows={3} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Full content (raw text)</label>
            <textarea value={form.full_content} onChange={(e) => onChange({ ...form, full_content: e.target.value })} rows={4} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-mono" />
          </div>
          <div className="flex flex-wrap gap-4">
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={form.is_active} onChange={(e) => onChange({ ...form, is_active: e.target.checked })} />
              Active (visible on site)
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={form.is_verified} onChange={(e) => onChange({ ...form, is_verified: e.target.checked })} />
              Verified badge
            </label>
          </div>
          <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
            <button type="button" onClick={onClose} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
              Cancel
            </button>
            <button type="submit" disabled={loading} className="rounded-lg bg-emerald-700 px-5 py-2 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50">
              {loading ? "Saving..." : "Save changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  required,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  required?: boolean;
  type?: string;
}) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-slate-700">{label}</label>
      <input
        type={type}
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
      />
    </div>
  );
}

function ActionBtn({
  label,
  icon: Icon,
  onClick,
}: {
  label: string;
  icon: typeof Bell;
  onClick: () => void;
}) {
  return (
    <button type="button" onClick={onClick} className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-1 text-xs text-slate-700 hover:bg-slate-200">
      <Icon className="h-3 w-3" />
      {label}
    </button>
  );
}

function SystemCard({
  title,
  desc,
  loading,
  onClick,
  icon: Icon,
}: {
  title: string;
  desc: string;
  loading: boolean;
  onClick: () => void;
  icon: typeof RefreshCw;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-2">
        <Icon className="h-5 w-5 text-sky-600" />
        <h3 className="font-bold text-slate-900">{title}</h3>
      </div>
      <p className="mt-2 text-sm text-slate-500">{desc}</p>
      <button type="button" disabled={loading} onClick={onClick} className="mt-4 rounded-lg bg-sky-700 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-800 disabled:opacity-50">
        Run
      </button>
    </div>
  );
}

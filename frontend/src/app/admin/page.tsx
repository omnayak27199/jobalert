"use client";

import {
  Bell,
  FileUp,
  LayoutDashboard,
  List,
  PlusCircle,
  RefreshCw,
  Settings,
  Trash2,
  Upload,
  Wrench,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  activateJob,
  createManualJob,
  deactivateJob,
  dispatchJobAlerts,
  fetchAdminJobs,
  fetchDashboard,
  getAdminKey,
  reEnrichJob,
  saveAdminKey,
  triggerCleanup,
  triggerEnrichAll,
  triggerFetch,
  triggerRepair,
  uploadPdf,
  type AdminDashboard,
  type AdminJob,
} from "@/lib/admin";
import { CATEGORY_LABELS, INDIAN_STATES, type JobCategory } from "@/lib/types";

type Tab = "dashboard" | "create" | "upload" | "jobs" | "system";

const TABS: { id: Tab; label: string; icon: typeof LayoutDashboard }[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
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
  last_date: "",
  exam_date: "",
  apply_url: "",
  notification_url: "",
  age_limit: "",
  application_fee: "",
  send_alerts: true,
};

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [adminKey, setAdminKey] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [dashboard, setDashboard] = useState<AdminDashboard | null>(null);
  const [jobs, setJobs] = useState<AdminJob[]>([]);
  const [jobSearch, setJobSearch] = useState("");
  const [form, setForm] = useState(EMPTY_FORM);
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [pdfMeta, setPdfMeta] = useState({ state: "", organization: "", title: "", apply_url: "", notification_url: "", send_alerts: true });

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

  const loadJobs = useCallback(async (q?: string) => {
    const data = await fetchAdminJobs(q);
    setJobs(data.jobs);
  }, []);

  useEffect(() => {
    const saved = getAdminKey();
    if (saved) {
      setAdminKey(saved);
      setAuthenticated(true);
    }
  }, []);

  useEffect(() => {
    if (!authenticated) return;
    if (tab === "dashboard") loadDashboard().catch((e) => setError(String(e)));
    if (tab === "jobs") loadJobs(jobSearch).catch((e) => setError(String(e)));
  }, [authenticated, tab, loadDashboard, loadJobs, jobSearch]);

  const handleLogin = () => {
    saveAdminKey(adminKey);
    setAuthenticated(true);
    clearStatus();
  };

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
        <h1 className="text-2xl font-bold text-slate-900">IndiaJob Admin</h1>
        <p className="mt-1 text-sm text-slate-500">Enter admin key to manage jobs and alerts</p>
        <input
          type="password"
          value={adminKey}
          onChange={(e) => setAdminKey(e.target.value)}
          placeholder="ADMIN_SECRET from server .env"
          className="mt-6 w-full rounded-lg border border-slate-200 px-4 py-3 text-sm"
        />
        <button
          type="button"
          onClick={handleLogin}
          className="mt-4 rounded-lg bg-sky-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-sky-800"
        >
          Enter Admin Panel
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">IndiaJob Admin Panel</h1>
          <p className="mt-1 text-sm text-slate-500">
            Upload notifications, create alerts manually, and control the portal
          </p>
        </div>
        <Link href="/" className="text-sm font-medium text-sky-700 hover:underline">
          ← Back to site
        </Link>
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
                        <Link href={`/job/${job.id}`} className="rounded bg-sky-50 px-2 py-1 text-xs text-sky-800 hover:bg-sky-100">View</Link>
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

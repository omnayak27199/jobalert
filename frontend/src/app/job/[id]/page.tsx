import Link from "next/link";
import {
  ArrowLeft,
  BadgeCheck,
  ExternalLink,
  FileText,
  MapPin,
  Users,
} from "lucide-react";
import { JobActions } from "@/components/JobActions";
import { JobAdvertisement } from "@/components/JobAdvertisement";
import { RelatedJobs } from "@/components/RelatedJobs";
import { getJob } from "@/lib/api";
import {
  formatDate,
  getCategoryAccent,
  getCategoryLabel,
} from "@/lib/utils";
import type { Job, JobAdvertisementSections, JobCategory } from "@/lib/types";
import { CATEGORY_LABELS } from "@/lib/types";

export const dynamic = "force-dynamic";

interface PageProps {
  params: Promise<{ id: string }>;
}

function resolvePdfUrl(job: Job, sections: JobAdvertisementSections | null | undefined): string | null {
  if (sections?.notification_pdf) return sections.notification_pdf;
  const notif = job.notification_url || "";
  if (notif.toLowerCase().includes(".pdf")) return notif;
  return null;
}

function StatChip({
  label,
  value,
  accent = "slate",
}: {
  label: string;
  value: string;
  accent?: "sky" | "red" | "emerald" | "slate";
}) {
  const styles = {
    sky: "border-sky-100 bg-sky-50 text-sky-900",
    red: "border-red-100 bg-red-50 text-red-900",
    emerald: "border-emerald-100 bg-emerald-50 text-emerald-900",
    slate: "border-slate-200 bg-slate-50 text-slate-900",
  };
  return (
    <div className={`rounded-xl border px-4 py-3 ${styles[accent]}`}>
      <p className="text-[11px] font-semibold uppercase tracking-wide opacity-70">{label}</p>
      <p className="mt-0.5 text-sm font-bold leading-snug">{value}</p>
    </div>
  );
}

export default async function JobDetailPage({ params }: PageProps) {
  const { id } = await params;
  let job: Job | null = null;

  try {
    job = await getJob(Number(id));
  } catch {
    // not found
  }

  if (!job) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-20 text-center">
        <h1 className="text-2xl font-bold text-slate-900">Notification Not Found</h1>
        <p className="mt-2 text-sm text-slate-500">
          This job may have closed or been removed from our listings.
        </p>
        <Link href="/" className="mt-6 inline-flex items-center gap-1 text-sm font-semibold text-sky-700 hover:underline">
          <ArrowLeft className="h-4 w-4" /> Back to home
        </Link>
      </div>
    );
  }

  const accent = getCategoryAccent(job.category);
  const categoryLabel = CATEGORY_LABELS[job.category as JobCategory] || getCategoryLabel(job.category);
  const sections = job.sections ?? {};
  const pdfUrl = resolvePdfUrl(job, sections);
  const isClosed = job.application_status === "closed";
  const applyUrl = isClosed
    ? null
    : job.apply_url && !job.apply_url.toLowerCase().includes(".pdf")
      ? job.apply_url
      : null;

  const lastDateLabel =
    sections?.dates?.find((d) => d.label.toLowerCase().includes("last"))?.date ??
    (job.last_date ? formatDate(job.last_date) : null);

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <nav className="mb-6 flex flex-wrap items-center gap-2 text-sm text-slate-500">
        <Link href="/" className="hover:text-sky-700">Home</Link>
        <span>/</span>
        <Link href="/jobs/notification" className="hover:text-sky-700">Job Alerts</Link>
        {job.state && (
          <>
            <span>/</span>
            <Link href={`/state/${encodeURIComponent(job.state)}`} className="hover:text-sky-700">{job.state}</Link>
          </>
        )}
        <span>/</span>
        <span className="max-w-[220px] truncate text-slate-400">{job.organization}</span>
      </nav>

      {/* Hero */}
      <header className="card-shadow mb-8 overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <div className="h-1.5" style={{ backgroundColor: accent }} />
        <div className="p-6 sm:p-8">
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <span
              className="rounded-md px-2.5 py-1 text-xs font-bold uppercase tracking-wide text-white"
              style={{ backgroundColor: accent }}
            >
              {categoryLabel}
            </span>
            <span className="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-bold uppercase tracking-wide text-slate-600">
              {job.organization}
            </span>
            {sections?.advertisement_no && (
              <span className="rounded-md bg-slate-800 px-2.5 py-1 text-xs font-medium text-white">
                {sections.advertisement_no}
              </span>
            )}
            {job.is_verified && (
              <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800 ring-1 ring-emerald-200">
                <BadgeCheck className="h-3.5 w-3.5" /> Verified
              </span>
            )}
            {isClosed && (
              <span className="rounded-md bg-slate-200 px-2.5 py-1 text-xs font-bold uppercase text-slate-700">
                Closed
              </span>
            )}
          </div>

          <h1 className="max-w-4xl break-words text-2xl font-bold leading-snug text-slate-900 sm:text-3xl">
            {job.title}
          </h1>
          {sections?.title_hi && (
            <p className="font-hindi mt-2 max-w-4xl break-words text-lg font-semibold leading-snug text-slate-700">
              {sections.title_hi}
            </p>
          )}

          {job.state && (
            <p className="mt-3 inline-flex items-center gap-1.5 text-sm text-slate-500">
              <MapPin className="h-4 w-4 shrink-0" /> {job.state}
            </p>
          )}

          {isClosed && job.last_date && (
            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
              <p className="text-sm font-semibold text-slate-800">
                Application closed on {formatDate(job.last_date)}
              </p>
            </div>
          )}

          <div className="mt-6 flex flex-wrap gap-3">
            {applyUrl && (
              <a
                href={applyUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-xl bg-sky-700 px-6 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-sky-800"
              >
                Apply Online <ExternalLink className="h-4 w-4" />
              </a>
            )}
            {pdfUrl && (
              <a
                href={pdfUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-xl border-2 border-amber-300 bg-amber-50 px-6 py-3 text-sm font-bold text-amber-950 transition hover:bg-amber-100"
              >
                <FileText className="h-4 w-4" /> Download Notification PDF
              </a>
            )}
            <JobActions jobId={job.id} />
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {job.vacancies != null && job.vacancies > 0 && (
              <StatChip label="Vacancies" value={job.vacancies.toLocaleString("en-IN")} accent="sky" />
            )}
            {lastDateLabel && (
              <StatChip
                label="Last Date"
                value={lastDateLabel}
                accent={isClosed ? "slate" : "red"}
              />
            )}
            {job.qualification && (
              <StatChip label="Qualification" value={job.qualification.slice(0, 80)} accent="emerald" />
            )}
            {job.published_date && (
              <StatChip label="Published" value={formatDate(job.published_date)} />
            )}
          </div>
        </div>
      </header>

      <div className="min-w-0">
        <JobAdvertisement sections={sections} job={job} />
        {job.organization && (
          <div className="mt-8">
            <RelatedJobs organization={job.organization} excludeId={job.id} />
          </div>
        )}
      </div>
    </div>
  );
}

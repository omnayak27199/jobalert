import { FavoriteButton } from "@/components/FavoriteButton";
import { cn, formatDate } from "@/lib/utils";
import {
  ArrowUpRight,
  BadgeCheck,
  Calendar,
  MapPin,
  Users,
} from "lucide-react";
import Link from "next/link";
import type { Job } from "@/lib/types";

interface JobCardProps {
  job: Job;
  compact?: boolean;
}

export function JobCard({ job, compact = false }: JobCardProps) {
  const isClosed = job.application_status === "closed";

  return (
    <article
      className={cn(
        "group card-shadow card-shadow-hover relative overflow-hidden rounded-lg border bg-white transition-all",
        isClosed ? "border-slate-200 opacity-90" : "border-slate-200",
        compact ? "p-3.5" : "p-4 sm:p-5"
      )}
    >
      <div
        className={cn(
          "absolute left-0 top-0 h-full w-1",
          isClosed ? "bg-slate-400" : "bg-sky-700"
        )}
      />
      <div className="flex flex-col gap-3 pl-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="max-w-full truncate rounded bg-slate-100 px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide text-slate-600">
              {job.organization}
            </span>
            {isClosed && (
              <span className="inline-flex shrink-0 rounded bg-slate-200 px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide text-slate-700">
                Closed
              </span>
            )}
            {job.is_verified && !isClosed && (
              <span className="inline-flex shrink-0 items-center gap-0.5 text-[11px] font-medium text-emerald-700">
                <BadgeCheck className="h-3 w-3" />
                Verified
              </span>
            )}
          </div>

          <h3
            className={cn(
              "line-clamp-2 font-semibold leading-snug group-hover:text-sky-800",
              isClosed ? "text-slate-600" : "text-slate-900",
              compact ? "text-sm" : "text-[15px] sm:text-base"
            )}
          >
            <Link href={`/job/${job.id}`} className="hover:underline">
              {job.title}
            </Link>
          </h3>

          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
            {job.vacancies && (
              <span className="inline-flex items-center gap-1">
                <Users className="h-3 w-3 shrink-0" />
                {job.vacancies.toLocaleString("en-IN")} posts
              </span>
            )}
            {job.state && (
              <span className="inline-flex max-w-[140px] items-center gap-1 truncate">
                <MapPin className="h-3 w-3 shrink-0" />
                {job.state}
              </span>
            )}
            {job.last_date && (
              <span
                className={cn(
                  "inline-flex items-center gap-1 font-medium",
                  isClosed ? "text-slate-500" : "text-red-700"
                )}
              >
                <Calendar className="h-3 w-3 shrink-0" />
                {isClosed ? "Closed" : "Last"}: {formatDate(job.last_date)}
              </span>
            )}
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2 sm:flex-col sm:items-end">
          <FavoriteButton jobId={job.id} />
          {isClosed ? (
            <span className="whitespace-nowrap rounded-md bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-600 ring-1 ring-slate-200">
              Application Closed
            </span>
          ) : job.days_left !== null && job.days_left !== undefined ? (
            <span
              className={cn(
                "whitespace-nowrap rounded-md px-2.5 py-1 text-xs font-bold",
                job.days_left <= 2
                  ? "bg-red-50 text-red-700 ring-1 ring-red-200"
                  : job.days_left <= 7
                    ? "bg-amber-50 text-amber-800 ring-1 ring-amber-200"
                    : "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200"
              )}
            >
              {job.days_left === 0 ? "Closes Today" : `${job.days_left} days left`}
            </span>
          ) : null}
          <Link
            href={`/job/${job.id}`}
            className={cn(
              "inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-xs font-semibold text-white transition",
              isClosed
                ? "bg-slate-500 hover:bg-slate-600"
                : "bg-sky-700 hover:bg-sky-800"
            )}
          >
            View
            <ArrowUpRight className="h-3 w-3" />
          </Link>
        </div>
      </div>
    </article>
  );
}

interface JobListProps {
  jobs: Job[];
  compact?: boolean;
  emptyMessage?: string;
}

export function JobList({
  jobs,
  compact,
  emptyMessage = "No notifications available at this time.",
}: JobListProps) {
  if (jobs.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-white py-16 text-center">
        <p className="text-sm font-medium text-slate-500">{emptyMessage}</p>
        <p className="mt-1 text-xs text-slate-400">
          Check back soon — we update listings daily from official sources.
        </p>
      </div>
    );
  }

  return (
    <div className={cn("space-y-2.5", !compact && "space-y-3")}>
      {jobs.map((job) => (
        <JobCard key={job.id} job={job} compact={compact} />
      ))}
    </div>
  );
}

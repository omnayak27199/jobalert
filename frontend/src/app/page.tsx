import Link from "next/link";
import {
  ArrowRight,
  CheckCircle2,
  MapPin,
  Search,
} from "lucide-react";
import { JobList } from "@/components/JobCard";
import { OfficialSources } from "@/components/OfficialSources";
import { SectionHeader } from "@/components/SectionHeader";
import {
  QuickAccess,
  StatsBar,
} from "@/components/StatsBar";
import { getJobs, getStats } from "@/lib/api";
import { PRIMARY_JOB_CATEGORY } from "@/lib/types";

export const revalidate = 60;

export default async function HomePage() {
  let stats = {
    total_jobs: 0,
    closing_soon: 0,
    today_updates: 0,
    states_covered: 0,
    verified_jobs: 0,
  };
  let closingSoon: Awaited<ReturnType<typeof getJobs>> = [];
  let latestJobs: Awaited<ReturnType<typeof getJobs>> = [];

  try {
    [stats, closingSoon, latestJobs] = await Promise.all([
      getStats(),
      getJobs({ category: PRIMARY_JOB_CATEGORY, closing_soon: true, limit: 6 }),
      getJobs({ category: PRIMARY_JOB_CATEGORY, limit: 12 }),
    ]);
  } catch {
    // API may not be running yet
  }

  return (
    <div>
      <section className="relative overflow-hidden bg-[#0c4a6e]">
        <div className="absolute inset-0 bg-gradient-to-br from-[#0c4a6e] via-[#075985] to-[#0e7490]" />
        <div className="absolute inset-0 opacity-10">
          <div className="absolute -right-20 -top-20 h-96 w-96 rounded-full bg-white/20 blur-3xl" />
          <div className="absolute -bottom-32 -left-20 h-80 w-80 rounded-full bg-sky-300/20 blur-3xl" />
        </div>

        <div className="relative mx-auto max-w-7xl px-4 py-14 sm:px-6 sm:py-16 lg:py-20">
          <div className="grid items-center gap-10 lg:grid-cols-2">
            <div>
              <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-sm text-sky-100 backdrop-blur">
                <CheckCircle2 className="h-4 w-4 text-emerald-300" />
                Free government job alerts — never miss a vacancy
              </div>
              <h1 className="text-3xl font-bold leading-tight tracking-tight text-white sm:text-4xl lg:text-[2.75rem] lg:leading-[1.15]">
                Get Daily{" "}
                <span className="text-sky-200">Sarkari Naukri</span> Job
                Alerts
              </h1>
              <p className="mt-5 max-w-xl text-base leading-relaxed text-sky-100/90 sm:text-lg">
                New recruitment notifications from UPSC, SSC, Railway, Banking,
                Defence and State PSCs — with vacancies, eligibility, last dates
                and direct official apply links.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link
                  href="/jobs/notification"
                  className="inline-flex items-center gap-2 rounded-lg bg-white px-6 py-3 text-sm font-bold text-sky-900 shadow-lg transition hover:bg-sky-50"
                >
                  View Job Alerts
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  href="/states"
                  className="inline-flex items-center gap-2 rounded-lg border border-white/25 bg-white/10 px-6 py-3 text-sm font-bold text-white backdrop-blur transition hover:bg-white/20"
                >
                  <MapPin className="h-4 w-4" />
                  Jobs by State
                </Link>
              </div>
            </div>

            <div className="card-shadow rounded-2xl border border-white/20 bg-white p-6 sm:p-8">
              <h2 className="text-lg font-bold text-slate-900">
                Find a Job Notification
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Search by post, department or recruiting organization
              </p>
              <Link
                href="/search"
                className="mt-5 flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-4 text-slate-400 transition hover:border-sky-200 hover:bg-white"
              >
                <Search className="h-5 w-5 shrink-0" />
                <span className="text-sm">
                  e.g. SSC CGL, RRB JE, IBPS Clerk, UP Police...
                </span>
              </Link>
              <div className="mt-6 grid grid-cols-2 gap-3 border-t border-slate-100 pt-6">
                {[
                  ["75+", "Govt Portals"],
                  ["32+", "States & UTs"],
                  ["Official", "Apply Links"],
                  ["Free", "Always"],
                ].map(([val, label]) => (
                  <div key={label}>
                    <p className="text-lg font-bold text-sky-800">{val}</p>
                    <p className="text-xs text-slate-500">{label}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <OfficialSources />

      <div className="mx-auto max-w-7xl px-4 pb-12 sm:px-6">
        <div className="pt-10">
          <StatsBar stats={stats} />
        </div>

        <div className="mt-10">
          <QuickAccess />
        </div>

        <div className="mt-10 space-y-10">
          {closingSoon.length > 0 && (
            <section>
              <SectionHeader
                title="Closing Soon"
                subtitle="Applications ending within the next 7 days — apply before the deadline"
                href="/jobs/notification?closing_soon=1"
                badge="Deadline Alert"
                badgeVariant="urgent"
              />
              <JobList jobs={closingSoon} compact />
            </section>
          )}

          <section>
            <SectionHeader
              title="Latest Job Alerts"
              subtitle="Most recent government recruitment notifications with vacancies and apply links"
              href="/jobs/notification"
              badge="Live"
              badgeVariant="live"
            />
            <JobList jobs={latestJobs} />
          </section>

          <div className="rounded-xl border border-sky-100 bg-sky-50 p-5">
            <h3 className="text-sm font-bold text-sky-900">
              Why IndiaJob.in?
            </h3>
            <ul className="mt-3 grid gap-2.5 sm:grid-cols-2">
              {[
                "Job notifications only — no exam clutter",
                "Vacancies, pay level & eligibility in one place",
                "Last date tracking so you never miss a deadline",
                "Direct links to official apply portals",
              ].map((text) => (
                <li
                  key={text}
                  className="flex items-start gap-2 text-xs leading-relaxed text-sky-800"
                >
                  <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" />
                  {text}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

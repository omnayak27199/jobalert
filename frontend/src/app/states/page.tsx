import Link from "next/link";
import { MapPin } from "lucide-react";
import { SectionHeader } from "@/components/SectionHeader";
import { getStates } from "@/lib/api";
import { INDIAN_STATES } from "@/lib/types";

export const revalidate = 120;

export default async function StatesPage() {
  let stateCounts: Awaited<ReturnType<typeof getStates>> = [];
  try {
    stateCounts = await getStates();
  } catch {
    // API not running
  }

  const countMap = new Map(stateCounts.map((s) => [s.state, s.count]));

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <div className="mb-8 rounded-xl border border-slate-200 bg-white p-6 sm:p-8">
        <SectionHeader
          title="State-wise Government Jobs"
          subtitle="Browse recruitment notifications organized by Indian states and union territories"
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        {INDIAN_STATES.map((state) => {
          const count = countMap.get(state) || 0;
          return (
            <Link
              key={state}
              href={`/state/${encodeURIComponent(state)}`}
              className="group card-shadow flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4 transition hover:-translate-y-0.5 hover:border-sky-200"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-sky-50 text-sky-700 transition group-hover:bg-sky-100">
                  <MapPin className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-semibold text-slate-900 group-hover:text-sky-800">
                    {state}
                  </p>
                  <p className="text-xs text-slate-400">
                    {count > 0
                      ? `${count} active listing${count > 1 ? "s" : ""}`
                      : "View notifications"}
                  </p>
                </div>
              </div>
              <span className="text-lg text-slate-300 transition group-hover:text-sky-500">
                →
              </span>
            </Link>
          );
        })}
      </div>

      <div className="card-shadow mt-10 rounded-xl border border-sky-100 bg-gradient-to-r from-sky-50 to-white p-6 sm:p-8">
        <h2 className="text-lg font-bold text-slate-900">All India Recruitments</h2>
        <p className="mt-1 max-w-2xl text-sm text-slate-500">
          Central government vacancies from UPSC, SSC, RRB, IBPS and other
          national recruiting bodies — applicable across all states.
        </p>
        <Link
          href="/jobs/notification"
          className="mt-5 inline-flex items-center rounded-lg bg-sky-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-sky-800"
        >
          View All India Jobs →
        </Link>
      </div>
    </div>
  );
}

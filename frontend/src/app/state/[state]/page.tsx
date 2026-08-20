import { JobList } from "@/components/JobCard";
import { SectionHeader } from "@/components/SectionHeader";
import { getJobs } from "@/lib/api";
import { PRIMARY_JOB_CATEGORY } from "@/lib/types";

export const dynamic = "force-dynamic";

interface PageProps {
  params: Promise<{ state: string }>;
}

export default async function StateDetailPage({ params }: PageProps) {
  const { state } = await params;
  const decodedState = decodeURIComponent(state);

  let jobs: Awaited<ReturnType<typeof getJobs>> = [];
  try {
    jobs = await getJobs({ state: decodedState, category: PRIMARY_JOB_CATEGORY, limit: 50 });
  } catch {
    // API not running
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <div className="mb-8 rounded-xl border border-slate-200 bg-white p-6 sm:p-8">
        <SectionHeader
          title={`${decodedState} — Job Alerts`}
          subtitle={`Government recruitment notifications from ${decodedState} — vacancies, eligibility and apply links`}
        />
      </div>

      <JobList
        jobs={jobs}
        emptyMessage={`No active listings for ${decodedState} right now. Check back soon.`}
      />
    </div>
  );
}

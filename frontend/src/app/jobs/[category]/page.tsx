import { redirect } from "next/navigation";
import { JobList } from "@/components/JobCard";
import { SectionHeader } from "@/components/SectionHeader";
import { getJobs } from "@/lib/api";
import { CATEGORY_LABELS, PRIMARY_JOB_CATEGORY, type JobCategory } from "@/lib/types";

export const dynamic = "force-dynamic";

interface PageProps {
  params: Promise<{ category: string }>;
  searchParams: Promise<{ closing_soon?: string }>;
}

export default async function CategoryPage({ params, searchParams }: PageProps) {
  const { category } = await params;
  const { closing_soon: closingSoonParam } = await searchParams;

  if (category !== PRIMARY_JOB_CATEGORY) {
    redirect("/jobs/notification");
  }

  const cat = category as JobCategory;
  const label = CATEGORY_LABELS[cat];
  const closingSoon = closingSoonParam === "1";

  let jobs: Awaited<ReturnType<typeof getJobs>> = [];
  try {
    jobs = await getJobs({
      category: cat,
      closing_soon: closingSoon,
      limit: 50,
    });
  } catch {
    // API not running
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <div className="mb-8 rounded-xl border border-slate-200 bg-white p-6 sm:p-8">
        <SectionHeader
          title={closingSoon ? "Closing Soon — Job Alerts" : label}
          subtitle={
            closingSoon
              ? "Recruitment notifications with application deadlines in the next 7 days"
              : "Government job recruitment notifications with vacancies, eligibility and official apply links"
          }
        />
      </div>

      <div className="mt-8">
        <JobList
          jobs={jobs}
          emptyMessage={
            closingSoon
              ? "No job alerts closing this week."
              : "No job notifications available at the moment."
          }
        />
      </div>
    </div>
  );
}

import Link from "next/link";
import { getJobs } from "@/lib/api";
import { PRIMARY_JOB_CATEGORY } from "@/lib/types";

export async function RelatedJobs({
  organization,
  excludeId,
}: {
  organization: string;
  excludeId: number;
}) {
  let related: Awaited<ReturnType<typeof getJobs>> = [];
  try {
    related = await getJobs({
      organization,
      category: PRIMARY_JOB_CATEGORY,
      limit: 5,
    });
  } catch {
    return null;
  }

  const items = related.filter((j) => j.id !== excludeId).slice(0, 4);
  if (items.length === 0) return null;

  return (
    <div className="card-shadow rounded-xl border border-slate-200 bg-white p-5">
      <h3 className="mb-3 text-sm font-bold text-slate-900">More from {organization}</h3>
      <ul className="space-y-3">
        {items.map((r) => (
          <li key={r.id}>
            <Link
              href={`/job/${r.id}`}
              className="line-clamp-2 text-sm font-medium leading-snug text-slate-800 hover:text-sky-800"
            >
              {r.title}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

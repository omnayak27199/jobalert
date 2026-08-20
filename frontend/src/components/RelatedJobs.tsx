"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getJobs } from "@/lib/api";
import type { Job } from "@/lib/types";
import { PRIMARY_JOB_CATEGORY } from "@/lib/types";

export function RelatedJobs({
  organization,
  excludeId,
}: {
  organization: string;
  excludeId: number;
}) {
  const [related, setRelated] = useState<Job[]>([]);

  useEffect(() => {
    let cancelled = false;
    getJobs({ search: organization, category: PRIMARY_JOB_CATEGORY, limit: 5 })
      .then((jobs) => {
        if (!cancelled) {
          setRelated(jobs.filter((j) => j.id !== excludeId).slice(0, 4));
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [organization, excludeId]);

  if (related.length === 0) return null;

  return (
    <div className="card-shadow rounded-xl border border-slate-200 bg-white p-5">
      <h3 className="mb-3 text-sm font-bold text-slate-900">More from {organization}</h3>
      <ul className="space-y-3">
        {related.map((r) => (
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

"use client";

import { Search } from "lucide-react";
import { useCallback, useState } from "react";
import { JobList } from "@/components/JobCard";
import { PRIMARY_JOB_CATEGORY } from "@/lib/types";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [jobs, setJobs] = useState<Awaited<ReturnType<typeof import("@/lib/api").getJobs>>>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!query.trim()) return;

      setLoading(true);
      setSearched(true);
      try {
        const res = await fetch(
          `/api/jobs?search=${encodeURIComponent(query)}&category=${PRIMARY_JOB_CATEGORY}&limit=50`,
        );
        const data = await res.json();
        setJobs(data);
      } catch {
        setJobs([]);
      } finally {
        setLoading(false);
      }
    },
    [query],
  );

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">
          Search Job Alerts
        </h1>
        <p className="mt-2 text-sm text-slate-500">
          Find recruitment notifications by post, department or organization
        </p>
      </div>

      <form
        onSubmit={handleSearch}
        className="card-shadow relative mx-auto max-w-2xl rounded-2xl border border-slate-200 bg-white p-2"
      >
        <Search className="absolute left-5 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search e.g. SSC CGL, RRB Group D, IBPS PO, UP Police..."
          className="w-full rounded-xl py-4 pl-12 pr-32 text-base text-slate-900 placeholder:text-slate-400 focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading}
          className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg bg-sky-700 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-sky-800 disabled:opacity-50"
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </form>

      <div className="mt-10">
        {searched && (
          <JobList
            jobs={jobs}
            emptyMessage={`No job alerts found for "${query}". Try a different keyword.`}
          />
        )}
      </div>
    </div>
  );
}

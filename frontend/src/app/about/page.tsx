import type { Metadata } from "next";
import Link from "next/link";
import { absoluteUrl, SITE_NAME } from "@/lib/seo";

export const metadata: Metadata = {
  title: "About Us",
  description:
    "IndiaGovJob is India's government job alert portal — sarkari naukri notifications from UPSC, SSC, RRB, IBPS and State PSC with official apply links.",
  alternates: { canonical: absoluteUrl("/about") },
};

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="text-3xl font-bold text-slate-900">About {SITE_NAME}</h1>
      <p className="mt-4 text-slate-600 leading-relaxed">
        {SITE_NAME} helps job seekers across India find government recruitment notifications
        (sarkari naukri) in one place — with vacancies, eligibility, last dates, and links to
        official apply portals.
      </p>
      <h2 className="mt-8 text-xl font-bold text-slate-900">What we publish</h2>
      <ul className="mt-3 list-disc space-y-2 pl-5 text-slate-600">
        <li>Recruitment notifications from UPSC, SSC, RRB, IBPS, State PSC and more</li>
        <li>Vacancy details parsed from official PDF notifications</li>
        <li>Last date, exam date, age limit and qualification summaries</li>
        <li>Direct links to official application websites — never aggregator apply forms</li>
      </ul>
      <h2 className="mt-8 text-xl font-bold text-slate-900">Disclaimer</h2>
      <p className="mt-3 text-slate-600 leading-relaxed">
        We are not affiliated with UPSC, SSC, RRB, IBPS or any recruiting agency. Always verify
        details on the official notification before applying.
      </p>
      <p className="mt-8">
        <Link href="/" className="font-semibold text-sky-700 hover:underline">
          ← Browse latest government jobs
        </Link>
      </p>
    </div>
  );
}

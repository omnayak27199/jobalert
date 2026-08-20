import type { Metadata } from "next";
import Link from "next/link";
import { absoluteUrl, SITE_NAME } from "@/lib/seo";

export const metadata: Metadata = {
  title: "Contact",
  description: `Contact ${SITE_NAME} for feedback, corrections, or partnership inquiries about government job listings.`,
  alternates: { canonical: absoluteUrl("/contact") },
};

export default function ContactPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="text-3xl font-bold text-slate-900">Contact Us</h1>
      <p className="mt-4 text-slate-600 leading-relaxed">
        Have feedback, spotted an error in a job listing, or want to report a broken official link?
        We&apos;d like to hear from you.
      </p>
      <div className="mt-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm font-semibold text-slate-700">Email</p>
        <a
          href="mailto:alerts@indiagovjob.online"
          className="mt-1 block text-sky-700 hover:underline"
        >
          alerts@indiagovjob.online
        </a>
        <p className="mt-6 text-sm text-slate-500">
          For job seekers: use the search page to find notifications, or create a free account to
          save jobs and get email alerts.
        </p>
      </div>
      <p className="mt-8">
        <Link href="/" className="font-semibold text-sky-700 hover:underline">
          ← Back to home
        </Link>
      </p>
    </div>
  );
}

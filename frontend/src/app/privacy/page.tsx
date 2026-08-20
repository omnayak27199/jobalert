import type { Metadata } from "next";
import Link from "next/link";
import { absoluteUrl, SITE_NAME } from "@/lib/seo";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: `Privacy policy for ${SITE_NAME} — how we handle account data, cookies, and email alerts.`,
  alternates: { canonical: absoluteUrl("/privacy") },
  robots: { index: true, follow: true },
};

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 prose prose-slate max-w-none">
      <h1 className="text-3xl font-bold text-slate-900">Privacy Policy</h1>
      <p className="mt-4 text-slate-600">Last updated: August 2026</p>

      <h2 className="mt-8 text-xl font-bold text-slate-900">Information we collect</h2>
      <p className="mt-2 text-slate-600 leading-relaxed">
        If you create an account, we store your name, email, optional phone number, and job alert
        preferences. We use this only to provide saved jobs and notification features.
      </p>

      <h2 className="mt-8 text-xl font-bold text-slate-900">Cookies &amp; local storage</h2>
      <p className="mt-2 text-slate-600 leading-relaxed">
        We use browser local storage to keep you signed in. We do not sell personal data to third
        parties.
      </p>

      <h2 className="mt-8 text-xl font-bold text-slate-900">Email &amp; WhatsApp alerts</h2>
      <p className="mt-2 text-slate-600 leading-relaxed">
        Alerts are sent only when you opt in. You can update preferences or delete your account at
        any time from your account page.
      </p>

      <h2 className="mt-8 text-xl font-bold text-slate-900">Contact</h2>
      <p className="mt-2 text-slate-600">
        Questions:{" "}
        <a href="mailto:alerts@indiagovjob.online" className="text-sky-700 hover:underline">
          alerts@indiagovjob.online
        </a>
      </p>

      <p className="mt-8">
        <Link href="/" className="font-semibold text-sky-700 hover:underline no-underline">
          ← {SITE_NAME} home
        </Link>
      </p>
    </div>
  );
}

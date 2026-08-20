import type { Metadata } from "next";
import type { Job } from "./types";

/** Public site URL — set NEXT_PUBLIC_SITE_URL in production. */
export const SITE_URL =
  (process.env.NEXT_PUBLIC_SITE_URL || "https://indiagovjob.online").replace(/\/$/, "");

export const SITE_NAME = "IndiaGovJob";
export const SITE_TAGLINE = "Government Jobs & Sarkari Naukri Alerts";

export const DEFAULT_DESCRIPTION =
  "Daily sarkari naukri and government job alerts from UPSC, SSC, RRB, IBPS and State PSC. Vacancies, eligibility, last dates and official apply links — updated daily.";

export const DEFAULT_KEYWORDS = [
  "government jobs",
  "sarkari naukri",
  "india job",
  "sarkari job",
  "UPSC recruitment",
  "SSC jobs",
  "RRB notification",
  "IBPS vacancy",
  "state PSC jobs",
  "government job alert",
  "सरकारी नौकरी",
];

export function absoluteUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${SITE_URL}${p}`;
}

export function buildRootMetadata(): Metadata {
  const googleVerification = process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION;

  return {
    metadataBase: new URL(SITE_URL),
    title: {
      default: `${SITE_NAME} — ${SITE_TAGLINE}`,
      template: `%s | ${SITE_NAME}`,
    },
    description: DEFAULT_DESCRIPTION,
    keywords: DEFAULT_KEYWORDS,
    authors: [{ name: SITE_NAME, url: SITE_URL }],
    creator: SITE_NAME,
    publisher: SITE_NAME,
    robots: {
      index: true,
      follow: true,
      googleBot: { index: true, follow: true, "max-image-preview": "large" },
    },
    alternates: { canonical: SITE_URL },
    openGraph: {
      type: "website",
      locale: "en_IN",
      url: SITE_URL,
      siteName: SITE_NAME,
      title: `${SITE_NAME} — ${SITE_TAGLINE}`,
      description: DEFAULT_DESCRIPTION,
    },
    twitter: {
      card: "summary_large_image",
      title: `${SITE_NAME} — ${SITE_TAGLINE}`,
      description: DEFAULT_DESCRIPTION,
    },
    ...(googleVerification
      ? { verification: { google: googleVerification } }
      : {}),
  };
}

export function buildJobMetadata(job: Job): Metadata {
  const title = job.title;
  const description = [
    job.organization,
    job.vacancies ? `${job.vacancies} vacancies` : null,
    job.last_date ? `Last date: ${job.last_date.slice(0, 10)}` : null,
    job.qualification ? job.qualification.slice(0, 80) : null,
    "Official apply link and eligibility on IndiaGovJob.",
  ]
    .filter(Boolean)
    .join(" · ");

  const url = absoluteUrl(`/job/${job.id}`);

  return {
    title,
    description: description.slice(0, 160),
    alternates: { canonical: url },
    openGraph: {
      type: "article",
      url,
      title,
      description: description.slice(0, 200),
      siteName: SITE_NAME,
    },
    twitter: {
      card: "summary",
      title,
      description: description.slice(0, 160),
    },
    keywords: [
      job.title,
      job.organization,
      job.state || "All India",
      "sarkari naukri",
      "government job",
    ],
  };
}

/** Schema.org JobPosting for Google rich results. */
export function jobPostingJsonLd(job: Job): Record<string, unknown> {
  const url = absoluteUrl(`/job/${job.id}`);
  const description =
    job.sections?.overview ||
    job.description ||
    `${job.organization} recruitment notification. Apply before the last date.`;

  const jsonLd: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    title: job.title,
    description: description.slice(0, 5000),
    identifier: {
      "@type": "PropertyValue",
      name: job.organization,
      value: String(job.id),
    },
    datePosted: job.published_date || undefined,
    hiringOrganization: {
      "@type": "Organization",
      name: job.organization,
      sameAs: job.source_url?.startsWith("http") ? job.source_url : undefined,
    },
    jobLocation: {
      "@type": "Place",
      address: {
        "@type": "PostalAddress",
        addressCountry: "IN",
        addressRegion: job.state || "India",
      },
    },
    applicantLocationRequirements: {
      "@type": "Country",
      name: "India",
    },
    employmentType: "FULL_TIME",
    url,
    directApply: Boolean(job.apply_url),
  };

  if (job.last_date) {
    jsonLd.validThrough = job.last_date;
  }
  if (job.qualification) {
    jsonLd.educationRequirements = job.qualification;
  }
  if (job.vacancies && job.vacancies > 0) {
    jsonLd.totalJobOpenings = job.vacancies;
  }
  if (job.apply_url) {
    jsonLd.applicationContact = {
      "@type": "ContactPoint",
      url: job.apply_url,
    };
  }

  return jsonLd;
}

export function organizationJsonLd(): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: SITE_NAME,
    url: SITE_URL,
    description: DEFAULT_DESCRIPTION,
    areaServed: { "@type": "Country", name: "India" },
  };
}

export function websiteJsonLd(): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: SITE_NAME,
    url: SITE_URL,
    description: DEFAULT_DESCRIPTION,
    inLanguage: ["en-IN", "hi-IN"],
    potentialAction: {
      "@type": "SearchAction",
      target: {
        "@type": "EntryPoint",
        urlTemplate: `${SITE_URL}/search?q={search_term_string}`,
      },
      "query-input": "required name=search_term_string",
    },
  };
}

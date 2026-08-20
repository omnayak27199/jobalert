import type { MetadataRoute } from "next";
import { getSitemapEntries } from "@/lib/api";
import { INDIAN_STATES } from "@/lib/types";
import { absoluteUrl, SITE_URL } from "@/lib/seo";

export const revalidate = 3600;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const staticPages: MetadataRoute.Sitemap = [
    { url: SITE_URL, lastModified: now, changeFrequency: "hourly", priority: 1 },
    { url: absoluteUrl("/jobs/notification"), lastModified: now, changeFrequency: "hourly", priority: 0.9 },
    { url: absoluteUrl("/jobs/notification?closing_soon=1"), lastModified: now, changeFrequency: "hourly", priority: 0.85 },
    { url: absoluteUrl("/states"), lastModified: now, changeFrequency: "daily", priority: 0.8 },
    { url: absoluteUrl("/search"), lastModified: now, changeFrequency: "weekly", priority: 0.7 },
    { url: absoluteUrl("/news"), lastModified: now, changeFrequency: "daily", priority: 0.6 },
    { url: absoluteUrl("/about"), lastModified: now, changeFrequency: "monthly", priority: 0.5 },
    { url: absoluteUrl("/contact"), lastModified: now, changeFrequency: "monthly", priority: 0.4 },
    { url: absoluteUrl("/privacy"), lastModified: now, changeFrequency: "yearly", priority: 0.3 },
  ];

  const statePages: MetadataRoute.Sitemap = INDIAN_STATES.map((state) => ({
    url: absoluteUrl(`/state/${encodeURIComponent(state)}`),
    lastModified: now,
    changeFrequency: "daily" as const,
    priority: 0.75,
  }));

  let jobPages: MetadataRoute.Sitemap = [];
  try {
    const entries = await getSitemapEntries();
    jobPages = entries.map((entry) => ({
      url: absoluteUrl(`/job/${entry.id}`),
      lastModified: entry.last_modified ? new Date(entry.last_modified) : now,
      changeFrequency: "daily" as const,
      priority: 0.8,
    }));
  } catch {
    // Backend unavailable during build — static pages still indexed
  }

  return [...staticPages, ...statePages, ...jobPages];
}

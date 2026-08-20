"use client";

import { FavoriteButton } from "@/components/FavoriteButton";

export function JobActions({ jobId }: { jobId: number }) {
  return <FavoriteButton jobId={jobId} className="px-4 py-2 text-sm" />;
}

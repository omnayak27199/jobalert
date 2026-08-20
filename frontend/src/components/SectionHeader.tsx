import { cn } from "@/lib/utils";
import { ArrowRight } from "lucide-react";
import Link from "next/link";

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  href?: string;
  linkLabel?: string;
  badge?: string;
  badgeVariant?: "live" | "urgent" | "default";
}

export function SectionHeader({
  title,
  subtitle,
  href,
  linkLabel = "View all",
  badge,
  badgeVariant = "default",
}: SectionHeaderProps) {
  return (
    <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <div className="mb-2 flex items-center gap-3">
          <div className="section-divider" />
          {badge && (
            <span
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide",
                badgeVariant === "live" && "bg-red-50 text-red-700",
                badgeVariant === "urgent" && "bg-amber-50 text-amber-800",
                badgeVariant === "default" && "bg-sky-50 text-sky-800"
              )}
            >
              {badgeVariant === "live" && (
                <span className="live-dot h-1.5 w-1.5 rounded-full bg-red-500" />
              )}
              {badge}
            </span>
          )}
        </div>
        <h2 className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">
          {title}
        </h2>
        {subtitle && (
          <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
        )}
      </div>
      {href && (
        <Link
          href={href}
          className="inline-flex items-center gap-1 text-sm font-semibold text-sky-700 hover:text-sky-900"
        >
          {linkLabel}
          <ArrowRight className="h-4 w-4" />
        </Link>
      )}
    </div>
  );
}

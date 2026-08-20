import type { Stats } from "@/lib/types";
import {
  Briefcase,
  Clock,
  Globe,
  MapPin,
  Search,
  ShieldCheck,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

interface StatsBarProps {
  stats: Stats;
}

export function StatsBar({ stats }: StatsBarProps) {
  const items = [
    {
      label: "Active Vacancies",
      value: stats.total_jobs,
      icon: Briefcase,
      desc: "Open recruitments",
    },
    {
      label: "Closing This Week",
      value: stats.closing_soon,
      icon: Clock,
      desc: "Apply before deadline",
      highlight: stats.closing_soon > 0,
    },
    {
      label: "Added Today",
      value: stats.today_updates,
      icon: Zap,
      desc: "New job alerts",
    },
    {
      label: "States & UTs",
      value: stats.states_covered,
      icon: Globe,
      desc: "Pan-India coverage",
    },
    {
      label: "Verified Dates",
      value: stats.verified_jobs,
      icon: ShieldCheck,
      desc: "Confirmed last dates",
    },
  ];

  return (
    <div className="-mt-8 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5 lg:gap-4">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <div
            key={item.label}
            className={cn(
              "card-shadow rounded-xl border bg-white p-4 transition hover:-translate-y-0.5",
              item.highlight
                ? "border-amber-200 ring-1 ring-amber-100"
                : "border-slate-200"
            )}
          >
            <div className="mb-3 flex items-center justify-between">
              <div
                className={cn(
                  "rounded-lg p-2",
                  item.highlight ? "bg-amber-50 text-amber-700" : "bg-sky-50 text-sky-700"
                )}
              >
                <Icon className="h-4 w-4" />
              </div>
            </div>
            <p className="text-2xl font-bold tabular-nums text-slate-900">
              {item.value.toLocaleString("en-IN")}
            </p>
            <p className="mt-0.5 text-sm font-semibold text-slate-700">
              {item.label}
            </p>
            <p className="text-[11px] text-slate-400">{item.desc}</p>
          </div>
        );
      })}
    </div>
  );
}

export function QuickAccess() {
  const links = [
    {
      href: "/jobs/notification",
      label: "Latest Job Alerts",
      desc: "New recruitment notifications",
      color: "bg-sky-600",
    },
    {
      href: "/jobs/notification?closing_soon=1",
      label: "Closing Soon",
      desc: "Deadlines this week",
      color: "bg-amber-600",
    },
    {
      href: "/states",
      label: "State-wise Jobs",
      desc: "Browse by your state",
      color: "bg-slate-700",
    },
    {
      href: "/search",
      label: "Search Jobs",
      desc: "Find by post or department",
      color: "bg-emerald-600",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {links.map((link) => {
        const Icon =
          link.href.includes("search") ? Search
          : link.href.includes("states") ? MapPin
          : link.href.includes("closing") ? Clock
          : Briefcase;
        return (
          <Link
            key={link.href}
            href={link.href}
            className="group card-shadow rounded-xl border border-slate-200 bg-white p-4 transition hover:-translate-y-0.5 hover:border-sky-200"
          >
            <div
              className={cn(
                "mb-3 inline-flex h-9 w-9 items-center justify-center rounded-lg text-white",
                link.color
              )}
            >
              <Icon className="h-4 w-4" />
            </div>
            <p className="font-semibold text-slate-900 group-hover:text-sky-800">
              {link.label}
            </p>
            <p className="mt-0.5 text-xs text-slate-500">{link.desc}</p>
          </Link>
        );
      })}
    </div>
  );
}

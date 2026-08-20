"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import {
  Clock,
  FileText,
  Home,
  LogOut,
  MapPin,
  Menu,
  Search,
  Shield,
  User,
  X,
} from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { cn } from "@/lib/utils";

const PRIMARY_NAV = [
  { href: "/", label: "Home", icon: Home, exact: true },
  { href: "/jobs/notification", label: "Job Alerts", icon: FileText },
  { href: "/jobs/notification?closing_soon=1", label: "Closing Soon", icon: Clock },
  { href: "/states", label: "By State", icon: MapPin },
];

function isActive(
  pathname: string,
  searchParams: URLSearchParams,
  href: string,
  exact = false,
) {
  const [path, query] = href.split("?");
  if (exact) {
    return pathname === path && !searchParams.get("closing_soon");
  }
  if (pathname !== path && !pathname.startsWith(`${path}/`)) {
    return false;
  }
  if (query?.includes("closing_soon=1")) {
    return searchParams.get("closing_soon") === "1";
  }
  if (path === "/jobs/notification") {
    return searchParams.get("closing_soon") !== "1";
  }
  return true;
}

function NavLink({
  href,
  label,
  active,
  compact = false,
}: {
  href: string;
  label: string;
  active: boolean;
  compact?: boolean;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "relative whitespace-nowrap font-medium transition-colors",
        compact ? "px-3 py-2 text-[13px]" : "px-4 py-2.5 text-sm",
        active
          ? "text-sky-800 after:absolute after:bottom-0 after:left-3 after:right-3 after:h-0.5 after:rounded-full after:bg-sky-700"
          : "text-slate-600 hover:text-sky-800"
      )}
    >
      {label}
    </Link>
  );
}

export function TrustBar() {
  return (
    <div className="border-b border-sky-900/20 bg-[#0c4a6e] text-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-1.5 text-[11px] sm:px-6 sm:text-xs">
        <div className="flex min-w-0 items-center gap-2">
          <Shield className="h-3 w-3 shrink-0 text-sky-300" />
          <span className="truncate text-sky-100">
            Government job alerts · Vacancies · Last dates · Official apply links
          </span>
        </div>
        <span className="inline-flex shrink-0 items-center gap-1.5 font-medium text-white">
          <span className="live-dot h-1.5 w-1.5 rounded-full bg-emerald-400" />
          Live Job Updates
        </span>
      </div>
    </div>
  );
}

export function Header() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user, logout } = useAuth();

  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4 sm:px-6 lg:h-[3.75rem]">
        <Link href="/" className="flex shrink-0 items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-[#0c4a6e]">
            <span className="text-sm font-black text-white">IJ</span>
          </div>
          <div className="hidden sm:block">
            <span className="text-lg font-bold leading-none tracking-tight text-slate-900">
              IndiaGovJob<span className="text-sky-700">.online</span>
            </span>
          </div>
        </Link>

        <nav className="hidden flex-1 items-center lg:flex">
          {PRIMARY_NAV.map((item) => (
            <NavLink
              key={item.href}
              href={item.href}
              label={item.label}
              active={isActive(pathname, searchParams, item.href, item.exact)}
              compact
            />
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-1.5 sm:gap-2">
          <Link
            href="/search"
            className="hidden items-center gap-2 rounded-md border border-slate-200 bg-slate-50/80 px-3 py-1.5 text-sm text-slate-500 transition hover:border-sky-200 hover:bg-white sm:flex"
          >
            <Search className="h-4 w-4 shrink-0 text-slate-400" />
            <span className="hidden xl:inline">Search jobs</span>
          </Link>
          <Link
            href="/search"
            className="rounded-md p-2 text-slate-500 hover:bg-slate-100 sm:hidden"
            aria-label="Search"
          >
            <Search className="h-5 w-5" />
          </Link>

          {user ? (
            <div className="hidden items-center sm:flex">
              {user.is_admin && (
                <Link
                  href="/admin"
                  className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-semibold text-amber-800 hover:bg-amber-50"
                >
                  <Shield className="h-4 w-4" />
                  <span className="hidden md:inline">Admin</span>
                </Link>
              )}
              <Link
                href="/account"
                className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-semibold text-sky-800 hover:bg-sky-50"
              >
                <User className="h-4 w-4" />
                <span className="hidden md:inline max-w-[80px] truncate">
                  {user.name.split(" ")[0]}
                </span>
              </Link>
              <button
                type="button"
                onClick={logout}
                className="rounded-md p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                aria-label="Sign out"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="hidden rounded-md bg-sky-700 px-4 py-1.5 text-sm font-semibold text-white hover:bg-sky-800 sm:inline-flex"
            >
              Sign in
            </Link>
          )}

          <button
            type="button"
            className="rounded-md p-2 text-slate-600 hover:bg-slate-100 lg:hidden"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Menu"
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <div className="border-t border-slate-100 bg-white lg:hidden">
          <nav className="mx-auto max-w-7xl px-4 py-3 sm:px-6">
            <div className="grid gap-0.5">
              {PRIMARY_NAV.map((item) => {
                const Icon = item.icon;
                const exact = "exact" in item && item.exact === true;
                const active = isActive(pathname, searchParams, item.href, exact);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileOpen(false)}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium",
                      active
                        ? "bg-sky-50 text-sky-800"
                        : "text-slate-700 hover:bg-slate-50"
                    )}
                  >
                    <Icon className="h-4 w-4 text-slate-400" />
                    {item.label}
                  </Link>
                );
              })}
            </div>
            <div className="mt-3 border-t border-slate-100 pt-3 sm:hidden">
              {user ? (
                <div className="flex flex-col gap-2">
                  {user.is_admin && (
                    <Link
                      href="/admin"
                      onClick={() => setMobileOpen(false)}
                      className="flex items-center justify-center gap-2 rounded-lg bg-amber-50 py-2.5 text-sm font-semibold text-amber-900"
                    >
                      <Shield className="h-4 w-4" />
                      Admin Panel
                    </Link>
                  )}
                  <div className="flex gap-2">
                  <Link
                    href="/account"
                    onClick={() => setMobileOpen(false)}
                    className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-sky-50 py-2.5 text-sm font-semibold text-sky-800"
                  >
                    <User className="h-4 w-4" />
                    My Account
                  </Link>
                  <button
                    type="button"
                    onClick={() => { logout(); setMobileOpen(false); }}
                    className="rounded-lg border border-slate-200 px-4 py-2.5 text-sm text-slate-600"
                  >
                    Sign out
                  </button>
                  </div>
                </div>
              ) : (
                <Link
                  href="/login"
                  onClick={() => setMobileOpen(false)}
                  className="block rounded-lg bg-sky-700 py-2.5 text-center text-sm font-semibold text-white"
                >
                  Sign in / Register
                </Link>
              )}
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}

export function Footer() {
  return (
    <footer className="mt-auto border-t border-slate-200 bg-[#1a2332] text-slate-300">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
          <div className="lg:col-span-1">
            <div className="mb-4 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-sky-700">
                <span className="text-sm font-black text-white">IJ</span>
              </div>
              <div>
                <span className="text-lg font-bold text-white">IndiaGovJob</span>
                <span className="text-sm font-semibold text-sky-400">.online</span>
              </div>
            </div>
            <p className="text-sm leading-relaxed text-slate-400">
              India&apos;s sarkari naukri portal — government job notifications,
              vacancies, eligibility, last dates and official apply links from
              verified sources.
            </p>
          </div>

          <div>
            <h4 className="mb-4 text-sm font-bold uppercase tracking-wider text-white">
              Job Alerts
            </h4>
            <ul className="space-y-2.5 text-sm">
              {[
                ["/jobs/notification", "Latest Notifications"],
                ["/jobs/notification?closing_soon=1", "Closing Soon"],
                ["/states", "State-wise Jobs"],
                ["/search", "Search Jobs"],
              ].map(([href, label]) => (
                <li key={href}>
                  <Link href={href} className="text-slate-400 hover:text-white">
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="mb-4 text-sm font-bold uppercase tracking-wider text-white">
              Popular Boards
            </h4>
            <ul className="space-y-2.5 text-sm text-slate-400">
              <li>UPSC · SSC · RRB</li>
              <li>IBPS · SBI · RBI</li>
              <li>State PSCs</li>
              <li>Police · Defence · Teaching</li>
            </ul>
          </div>

          <div>
            <h4 className="mb-4 text-sm font-bold uppercase tracking-wider text-white">
              Company
            </h4>
            <ul className="space-y-2.5 text-sm">
              {[
                ["/about", "About Us"],
                ["/contact", "Contact"],
                ["/privacy", "Privacy Policy"],
              ].map(([href, label]) => (
                <li key={href}>
                  <Link href={href} className="text-slate-400 hover:text-white">
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="mb-4 text-sm font-bold uppercase tracking-wider text-white">
              Official Sources
            </h4>
            <ul className="space-y-2.5 text-sm text-slate-400">
              <li>upsc.gov.in</li>
              <li>ssc.nic.in</li>
              <li>rrbcdg.gov.in</li>
              <li>ibps.in</li>
              <li>employmentnews.gov.in</li>
            </ul>
          </div>
        </div>

        <div className="mt-10 rounded-lg border border-slate-700 bg-slate-800/50 p-4">
          <p className="text-xs leading-relaxed text-slate-400">
            <strong className="text-slate-300">Disclaimer:</strong> IndiaGovJob.online
            publishes government job and sarkari naukri notifications only. We are not
            affiliated with UPSC, SSC, RRB, IBPS or any recruiting agency.
            Always verify details and apply only through official portals.
          </p>
        </div>

        <div className="mt-8 flex flex-col items-center justify-between gap-4 border-t border-slate-700 pt-6 text-xs text-slate-500 sm:flex-row">
          <p>© {new Date().getFullYear()} IndiaGovJob.online — All rights reserved.</p>
          <p>Made for job seekers across India 🇮🇳</p>
        </div>
      </div>
    </footer>
  );
}

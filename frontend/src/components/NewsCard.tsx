import Link from "next/link";
import { ArrowUpRight, Megaphone } from "lucide-react";
import type { NewsItem } from "@/lib/types";
import { formatDate } from "@/lib/utils";

interface NewsCardProps {
  item: NewsItem;
}

export function NewsCard({ item }: NewsCardProps) {
  return (
    <article className="group card-shadow rounded-lg border border-slate-200 bg-white p-5 transition hover:border-sky-200">
      <div className="flex items-start gap-4">
        {item.is_important && (
          <div className="mt-0.5 shrink-0 rounded-lg bg-amber-50 p-2.5 ring-1 ring-amber-100">
            <Megaphone className="h-4 w-4 text-amber-700" />
          </div>
        )}
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded bg-slate-100 px-2 py-0.5 font-semibold uppercase tracking-wide text-slate-600">
              {item.source}
            </span>
            <span className="text-slate-400">{formatDate(item.published_at)}</span>
            {item.is_important && (
              <span className="rounded bg-amber-100 px-2 py-0.5 font-semibold text-amber-800">
                Important
              </span>
            )}
          </div>
          <h3 className="font-semibold leading-snug text-slate-900 group-hover:text-sky-800">
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-start gap-1 hover:underline"
            >
              {item.title}
              <ArrowUpRight className="mt-0.5 h-3.5 w-3.5 shrink-0 opacity-50" />
            </a>
          </h3>
          {item.summary && (
            <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-slate-500">
              {item.summary}
            </p>
          )}
        </div>
      </div>
    </article>
  );
}

interface NewsListProps {
  items: NewsItem[];
}

export function NewsList({ items }: NewsListProps) {
  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-white py-16 text-center">
        <p className="text-sm font-medium text-slate-500">No news available.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {items.map((item) => (
        <NewsCard key={item.id} item={item} />
      ))}
    </div>
  );
}

export function NewsSidebar({ items }: NewsListProps) {
  return (
    <aside className="card-shadow sticky top-36 rounded-xl border border-slate-200 bg-white">
      <div className="border-b border-slate-100 px-5 py-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900">Latest News</h2>
          <Link
            href="/news"
            className="text-xs font-semibold text-sky-700 hover:text-sky-900"
          >
            All news →
          </Link>
        </div>
        <p className="mt-0.5 text-xs text-slate-500">
          Recruitment & exam updates
        </p>
      </div>
      <div className="divide-y divide-slate-100">
        {items.slice(0, 6).map((item) => (
          <div key={item.id} className="px-5 py-3.5 transition hover:bg-slate-50">
            {item.is_important && (
              <span className="mb-1 inline-block rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-800">
                Important
              </span>
            )}
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block text-sm font-medium leading-snug text-slate-800 hover:text-sky-800"
            >
              {item.title}
            </a>
            <p className="mt-1 text-[11px] text-slate-400">
              {item.source} · {formatDate(item.published_at)}
            </p>
          </div>
        ))}
        {items.length === 0 && (
          <p className="px-5 py-8 text-center text-sm text-slate-400">
            No news at the moment
          </p>
        )}
      </div>
    </aside>
  );
}

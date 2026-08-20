import { NewsList } from "@/components/NewsCard";
import { SectionHeader } from "@/components/SectionHeader";
import { getNews } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function NewsPage() {
  let news: Awaited<ReturnType<typeof getNews>> = [];
  try {
    news = await getNews(false);
  } catch {
    // API not running
  }

  const important = news.filter((n) => n.is_important);
  const regular = news.filter((n) => !n.is_important);

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <div className="mb-8 rounded-xl border border-slate-200 bg-white p-6 sm:p-8">
        <SectionHeader
          title="Recruitment & Exam News"
          subtitle="Important updates on government jobs, exams, counselling and results"
        />
      </div>

      {important.length > 0 && (
        <section className="mb-10">
          <SectionHeader
            title="Important Updates"
            badge="Priority"
            badgeVariant="urgent"
          />
          <NewsList items={important} />
        </section>
      )}

      {regular.length > 0 && (
        <section>
          <SectionHeader title="All News" />
          <NewsList items={regular} />
        </section>
      )}

      {news.length === 0 && <NewsList items={[]} />}
    </div>
  );
}

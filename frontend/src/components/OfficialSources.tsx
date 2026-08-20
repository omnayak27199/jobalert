const OFFICIAL_SOURCES = [
  "UPSC",
  "SSC",
  "RRB",
  "IBPS",
  "SBI",
  "ISRO",
  "DRDO",
  "NTPC",
  "State PSC",
  "Employment News",
  "UPSC",
  "SSC",
  "RRB",
  "IBPS",
  "SBI",
  "ISRO",
  "DRDO",
  "NTPC",
  "State PSC",
  "Employment News",
];

export function OfficialSources() {
  return (
    <section className="border-y border-slate-200 bg-white py-6">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <p className="mb-4 text-center text-xs font-semibold uppercase tracking-widest text-slate-400">
          Job alerts sourced from official government portals
        </p>
        <div className="relative overflow-hidden">
          <div className="marquee-track flex w-max gap-8">
            {OFFICIAL_SOURCES.map((org, i) => (
              <span
                key={`${org}-${i}`}
                className="shrink-0 rounded-lg border border-slate-200 bg-slate-50 px-5 py-2 text-sm font-semibold text-slate-600"
              >
                {org}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

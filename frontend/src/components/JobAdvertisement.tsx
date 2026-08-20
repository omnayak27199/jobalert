"use client";

import type { ReactNode } from "react";
import { ExternalLink, FileText } from "lucide-react";
import type { DateRow, Job, JobAdvertisementSections } from "@/lib/types";

export type { JobAdvertisementSections };

function display(value: string | number | null | undefined): string {
  if (value == null) return "";
  const text = String(value).trim();
  if (!text || /see official|see notification|see pdf/i.test(text)) return "";
  return text;
}

function findDate(dates: DateRow[], kind: "start" | "last"): string {
  const match = dates.find((d) => {
    const label = d.label.toLowerCase();
    return kind === "last"
      ? label.includes("last")
      : label.includes("start") || label.includes("opening");
  });
  return match?.date ?? "";
}

function NotificationTable({
  headers,
  rows,
}: {
  headers: string[];
  rows: string[][];
}) {
  if (rows.length === 0) return null;
  return (
    <div className="my-4 overflow-x-auto">
      <table className="w-full min-w-[480px] border-collapse border border-slate-300 text-sm">
        <thead>
          <tr className="bg-slate-100">
            {headers.map((h) => (
              <th
                key={h}
                className="border border-slate-300 px-3 py-2 text-left text-xs font-bold uppercase text-slate-800"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri} className={ri % 2 === 1 ? "bg-slate-50" : "bg-white"}>
              {row.map((cell, ci) => (
                <td
                  key={ci}
                  className="border border-slate-300 px-3 py-2 align-top text-slate-800 [overflow-wrap:anywhere]"
                >
                  {cell || "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ArticleSection({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="border-b border-slate-200 py-8 last:border-b-0">
      <h2 className="mb-4 text-xl font-bold text-slate-900">{title}</h2>
      {children}
    </section>
  );
}

interface JobAdvertisementProps {
  sections: JobAdvertisementSections;
  job?: Pick<
    Job,
    "title" | "organization" | "state" | "vacancies" | "apply_url" | "notification_url" | "qualification" | "age_limit" | "application_fee"
  >;
}

export function JobAdvertisement({ sections, job }: JobAdvertisementProps) {
  const dates = sections.dates ?? [];
  const vacancyRows = sections.vacancy_rows ?? [];
  const opening = findDate(dates, "start");
  const closing = findDate(dates, "last");
  const totalVac = sections.total_vacancies ?? job?.vacancies;
  const org = sections.organization ?? job?.organization ?? "";
  const title = sections.title ?? job?.title ?? "Recruitment Notification";

  const hasPay = vacancyRows.some((r) => display(r.pay_scale) || display(r.pay_level));
  const hasQual = vacancyRows.some((r) => display(r.qualification));

  const vacancyHeaders = [
    "Sr.",
    "Post Name",
    "Vacancies",
    ...(hasQual ? ["Qualification"] : []),
    ...(hasPay ? ["Pay Level", "Pay Scale (7th CPC)"] : []),
  ];

  const vacancyTableRows = vacancyRows.map((r) => {
    const row = [
      r.sr,
      r.post_hi ? `${r.post}\n${r.post_hi}` : r.post,
      r.vacancies > 0 ? String(r.vacancies) : "—",
    ];
    if (hasQual) row.push(display(r.qualification) || "—");
    if (hasPay) {
      row.push(display(r.pay_level) || "—");
      row.push(display(r.pay_scale) || "—");
    }
    return row;
  });

  const overviewRows: string[][] = [
    ["Organization", org],
    ["Advertisement", display(sections.advertisement_no) || "—"],
    ["Post(s)", vacancyRows.length > 0 ? vacancyRows.map((r) => r.post).join("; ") : title],
    ["Total Vacancies", totalVac ? String(totalVac) : "—"],
    ["Job Location", job?.state ?? "—"],
    ["Application Start Date", opening || "—"],
    ["Application Last Date", closing || "—"],
    ["Application Mode", job?.apply_url ? "Online" : "As per notification"],
    ["Qualification", display(sections.qualification_summary) || display(job?.qualification) || "See vacancy table below"],
    ["Age Limit", display(sections.age_limit) || display(job?.age_limit) || "—"],
    ["Application Fee", display(job?.application_fee) || (sections.application_fee_rows?.[0]?.[1] ?? "—")],
  ].filter(([, val]) => val !== "—" || true);

  const dateRows = dates.map((d) => [d.label, d.date]);

  const feeRows = (sections.application_fee_rows ?? []).map(([cat, fee]) => [cat, fee]);

  const docs = sections.documents ?? [];
  const pdfUrl = sections.notification_pdf ?? job?.notification_url ?? null;
  const applyUrl = job?.apply_url && !job.apply_url.toLowerCase().includes(".pdf") ? job.apply_url : null;

  const introParts: string[] = [];
  if (org) introParts.push(`${org} has published a recruitment notification`);
  if (sections.advertisement_no) introParts.push(`(${sections.advertisement_no})`);
  if (totalVac) introParts.push(`for ${totalVac.toLocaleString("en-IN")} vacancy/vacancies.`);
  else introParts.push("for various posts.");
  if (opening && closing) {
    introParts.push(`Online applications are accepted from ${opening} to ${closing}.`);
  } else if (closing) {
    introParts.push(`Last date to apply is ${closing}.`);
  }
  if (display(sections.qualification_summary) || display(job?.qualification)) {
    introParts.push(
      `Candidates with ${display(sections.qualification_summary) || display(job?.qualification)} are eligible to apply.`,
    );
  }

  const toc = [
    { id: "overview", label: "Overview" },
    dates.length > 0 && { id: "dates", label: "Important Dates" },
    vacancyRows.length > 0 && { id: "vacancy", label: "Vacancy Details" },
    (sections.eligibility_rows?.length || display(sections.qualification_summary) || display(job?.qualification)) && {
      id: "eligibility",
      label: "Eligibility Criteria",
    },
    (display(sections.age_limit) || display(sections.age_relaxation)) && {
      id: "age",
      label: "Age Limit",
    },
    feeRows.length > 0 && { id: "fee", label: "Application Fee" },
    sections.selection_steps?.length && { id: "selection", label: "Selection Process" },
    { id: "links", label: "Important Links" },
  ].filter(Boolean) as { id: string; label: string }[];

  return (
    <article className="min-w-0 rounded-xl border border-slate-200 bg-white px-5 py-2 sm:px-8">
      {/* Table of contents — like FreeJobAlert */}
      <nav className="border-b border-slate-200 py-5">
        <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">
          Table of Contents
        </p>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
          {toc.map((item) => (
            <a
              key={item.id}
              href={`#${item.id}`}
              className="text-sky-700 hover:text-sky-900 hover:underline"
            >
              {item.label}
            </a>
          ))}
        </div>
      </nav>

      <p className="py-6 text-base leading-relaxed text-slate-700">{introParts.join(" ")}</p>

      {sections.overview && (
        <p className="mb-4 text-sm leading-relaxed text-slate-600">{sections.overview}</p>
      )}
      {sections.overview_hi && (
        <p className="font-hindi mb-6 text-sm leading-relaxed text-slate-700">{sections.overview_hi}</p>
      )}

      <ArticleSection id="overview" title={`${org || "Recruitment"} Overview`}>
        <p className="mb-3 text-sm text-slate-600">
          Key particulars from the official notification:
        </p>
        <NotificationTable headers={["Particulars", "Details"]} rows={overviewRows} />
      </ArticleSection>

      {dateRows.length > 0 && (
        <ArticleSection id="dates" title="Important Dates">
          <NotificationTable headers={["Event", "Date"]} rows={dateRows} />
        </ArticleSection>
      )}

      {vacancyRows.length > 0 && (
        <ArticleSection id="vacancy" title="Vacancy Details">
          <p className="mb-2 text-sm text-slate-600">
            Post-wise vacancy break-up as given in the official notification
            {totalVac ? ` (Total: ${totalVac.toLocaleString("en-IN")})` : ""}:
          </p>
          <NotificationTable headers={vacancyHeaders} rows={vacancyTableRows} />
        </ArticleSection>
      )}

      {(sections.eligibility_rows?.length ||
        display(sections.qualification_summary) ||
        display(job?.qualification)) && (
        <ArticleSection id="eligibility" title="Eligibility Criteria">
          <p className="mb-4 text-sm text-slate-600">
            Educational qualification and experience requirements vary by post:
          </p>
          {sections.eligibility_rows?.map((row) => (
            <div key={row.post} className="mb-5">
              <h3 className="mb-2 text-base font-bold text-slate-900">{row.post}</h3>
              <ul className="list-disc space-y-1 pl-5 text-sm leading-relaxed text-slate-700">
                {display(row.education) && <li>{row.education}</li>}
                {display(row.experience) && <li>Experience: {row.experience}</li>}
                {display(row.other) && <li>{row.other}</li>}
              </ul>
            </div>
          ))}
          {!sections.eligibility_rows?.length &&
            vacancyRows
              .filter((r) => display(r.qualification))
              .map((r) => (
                <div key={r.sr} className="mb-5">
                  <h3 className="mb-2 text-base font-bold text-slate-900">{r.post}</h3>
                  <ul className="list-disc pl-5 text-sm text-slate-700">
                    <li>{r.qualification}</li>
                  </ul>
                </div>
              ))}
          {!sections.eligibility_rows?.length &&
            !vacancyRows.some((r) => display(r.qualification)) &&
            display(sections.qualification_summary || job?.qualification) && (
              <ul className="list-disc pl-5 text-sm leading-relaxed text-slate-700">
                <li>{display(sections.qualification_summary) || display(job?.qualification)}</li>
              </ul>
            )}
        </ArticleSection>
      )}

      {(display(sections.age_limit) || display(sections.age_relaxation)) && (
        <ArticleSection id="age" title="Age Limit">
          {display(sections.age_limit) && (
            <p className="text-sm text-slate-700">
              <strong>Age limit:</strong> {sections.age_limit}
            </p>
          )}
          {display(sections.age_relaxation) && (
            <p className="mt-2 text-sm text-slate-700">
              <strong>Age relaxation:</strong> {sections.age_relaxation}
            </p>
          )}
        </ArticleSection>
      )}

      {feeRows.length > 0 && (
        <ArticleSection id="fee" title="Application Fee">
          <NotificationTable headers={["Category", "Fee"]} rows={feeRows} />
        </ArticleSection>
      )}

      {sections.selection_steps && sections.selection_steps.length > 0 && (
        <ArticleSection id="selection" title="Selection Process">
          <ol className="list-decimal space-y-2 pl-5 text-sm leading-relaxed text-slate-700">
            {sections.selection_steps.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>
        </ArticleSection>
      )}

      {sections.reservation && sections.reservation.length > 0 && (
        <ArticleSection id="reservation" title="Reservation">
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
            {sections.reservation.map((note, i) => (
              <li key={i}>{note}</li>
            ))}
          </ul>
        </ArticleSection>
      )}

      {sections.special_notes && sections.special_notes.length > 0 && (
        <ArticleSection id="notes" title="Important Instructions">
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
            {sections.special_notes.map((note, i) => (
              <li key={i}>{note}</li>
            ))}
          </ul>
        </ArticleSection>
      )}

      <ArticleSection id="links" title="Important Links">
        <div className="space-y-2">
          {pdfUrl && (
            <a
              href={pdfUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-950 hover:bg-amber-100"
            >
              <FileText className="h-4 w-4 shrink-0" />
              Download Official Notification PDF
              <ExternalLink className="ml-auto h-4 w-4 opacity-60" />
            </a>
          )}
          {applyUrl && (
            <a
              href={applyUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm font-semibold text-sky-900 hover:bg-sky-100"
            >
              Apply Online on Official Portal
              <ExternalLink className="ml-auto h-4 w-4 opacity-60" />
            </a>
          )}
          {docs.map((doc) => (
            <a
              key={doc.url}
              href={doc.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-800 hover:bg-slate-100"
            >
              <FileText className="h-4 w-4 shrink-0 text-sky-600" />
              {doc.label}
              <ExternalLink className="ml-auto h-4 w-4 opacity-60" />
            </a>
          ))}
        </div>
      </ArticleSection>
    </article>
  );
}

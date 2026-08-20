import { cn } from "@/lib/utils";

export function formatDate(dateStr: string | null): string {
  if (!dateStr) return "Not specified";
  return new Date(dateStr).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function getCategoryAccent(category: string): string {
  const colors: Record<string, string> = {
    notification: "#0369a1",
    admit_card: "#7c3aed",
    result: "#047857",
    answer_key: "#c2410c",
    syllabus: "#4338ca",
    education: "#be185d",
  };
  return colors[category] || "#475569";
}

export function getCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    notification: "Notification",
    admit_card: "Admit Card",
    result: "Result",
    answer_key: "Answer Key",
    syllabus: "Syllabus",
    education: "Education",
  };
  return labels[category] || category;
}

export function getUrgencyColor(daysLeft: number | null): string {
  if (daysLeft === null) return "bg-slate-100 text-slate-600";
  if (daysLeft <= 2) return "bg-red-50 text-red-700 ring-1 ring-red-200";
  if (daysLeft <= 7) return "bg-amber-50 text-amber-800 ring-1 ring-amber-200";
  return "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200";
}

export function getCategoryColor(category: string): string {
  const colors: Record<string, string> = {
    notification: "bg-sky-50 text-sky-800 border-sky-200",
    admit_card: "bg-violet-50 text-violet-800 border-violet-200",
    result: "bg-emerald-50 text-emerald-800 border-emerald-200",
    answer_key: "bg-orange-50 text-orange-800 border-orange-200",
    syllabus: "bg-indigo-50 text-indigo-800 border-indigo-200",
    education: "bg-rose-50 text-rose-800 border-rose-200",
  };
  return colors[category] || "bg-slate-50 text-slate-700 border-slate-200";
}

export { cn } from "./cn";

export interface JobAdvertisementSections {
  title?: string;
  title_hi?: string;
  organization?: string;
  advertisement_no?: string;
  total_vacancies?: number;
  overview?: string;
  overview_hi?: string;
  qualification_summary?: string;
  vacancy_rows?: VacancyRow[];
  eligibility_rows?: EligibilityRow[];
  age_limit?: string;
  age_relaxation?: string;
  application_fee_rows?: [string, string][];
  dates?: DateRow[];
  selection_steps?: string[];
  reservation?: string[];
  special_notes?: string[];
  syllabus_url?: string | null;
  syllabus_note?: string;
  documents?: DocumentLink[];
  notification_pdf?: string | null;
}

export interface VacancyRow {
  sr: string;
  post: string;
  post_hi?: string;
  vacancies: number;
  pay_level: string;
  pay_scale: string;
  qualification: string;
}

export interface EligibilityRow {
  post: string;
  education: string;
  experience: string;
  other: string;
}

export interface DateRow {
  label: string;
  label_hi?: string;
  date: string;
}

export interface DocumentLink {
  label: string;
  url: string;
}

export interface Job {
  id: number;
  title: string;
  organization: string;
  category: string;
  scope: string;
  state: string | null;
  vacancies: number | null;
  apply_url: string | null;
  source_url: string;
  source_name: string;
  published_date: string | null;
  last_date: string | null;
  exam_date: string | null;
  qualification: string | null;
  description: string | null;
  full_content: string | null;
  notification_url: string | null;
  age_limit: string | null;
  application_fee: string | null;
  sections?: JobAdvertisementSections | null;
  application_status?: "open" | "closed" | "unknown";
  days_since_closed?: number | null;
  is_verified: boolean;
  days_left: number | null;
}

export interface NewsItem {
  id: number;
  title: string;
  summary: string | null;
  url: string;
  source: string;
  category: string;
  is_important: boolean;
  published_at: string | null;
}

export interface Stats {
  total_jobs: number;
  closing_soon: number;
  today_updates: number;
  states_covered: number;
  verified_jobs: number;
}

export interface StateCount {
  state: string;
  count: number;
}

export type JobCategory =
  | "notification"
  | "admit_card"
  | "result"
  | "answer_key"
  | "syllabus"
  | "education";

/** Public site only lists recruitment notifications — not admit cards, results, or syllabus. */
export const PRIMARY_JOB_CATEGORY: JobCategory = "notification";

export const CATEGORY_LABELS: Record<JobCategory, string> = {
  notification: "Job Notifications",
  admit_card: "Admit Cards",
  result: "Results",
  answer_key: "Answer Keys",
  syllabus: "Syllabus",
  education: "Education",
};

export const CATEGORY_ICONS: Record<JobCategory, string> = {
  notification: "📋",
  admit_card: "🎫",
  result: "🏆",
  answer_key: "📝",
  syllabus: "📚",
  education: "🎓",
};

export const INDIAN_STATES = [
  "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
  "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
  "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
  "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan",
  "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
  "Uttarakhand", "West Bengal", "Jammu and Kashmir", "Ladakh", "Puducherry",
];

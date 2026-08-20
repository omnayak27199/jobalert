"use client";

import {
  Bell,
  Briefcase,
  GraduationCap,
  Heart,
  Mail,
  MessageCircle,
  Save,
  Shield,
  Sparkles,
  User,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { JobList } from "@/components/JobCard";
import {
  getFavorites,
  getMatchedJobs,
  getPreferences,
  getProfile,
  updateMe,
  updatePreferences,
  updateProfile,
  type EducationEntry,
  type ExperienceEntry,
  type MatchedJob,
  type UserPreferences,
  type UserProfile,
} from "@/lib/auth";
import type { Job } from "@/lib/types";
import { INDIAN_STATES } from "@/lib/types";

const CATEGORIES = [{ value: "notification", label: "Job Notifications" }];

const QUALIFICATIONS = [
  "10th Pass",
  "12th Pass",
  "ITI",
  "Diploma",
  "Graduate",
  "Post Graduate",
  "Engineering",
  "Medical",
];

const GENDERS = ["Male", "Female", "Other"];
const CATEGORIES_CANDIDATE = ["General", "OBC", "SC", "ST", "EWS"];

type Tab = "profile" | "for-you" | "alerts" | "saved";

const emptyProfile = (): UserProfile => ({
  education: [],
  experience: [],
  skills: [],
  preferred_posts: [],
  preferred_departments: [],
  profile_complete: false,
  stats: {
    completeness_percent: 0,
    education_entries: 0,
    experience_entries: 0,
    profile_complete: false,
  },
});

export default function AccountPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("profile");
  const [prefs, setPrefs] = useState<UserPreferences>({
    states: [],
    categories: ["notification"],
    qualifications: [],
    organizations: [],
    email_alerts: true,
    whatsapp_alerts: false,
    alert_frequency: "instant",
  });
  const [profile, setProfile] = useState<UserProfile>(emptyProfile());
  const [phone, setPhone] = useState("");
  const [savedJobs, setSavedJobs] = useState<Job[]>([]);
  const [matchedJobs, setMatchedJobs] = useState<MatchedJob[]>([]);
  const [profileComplete, setProfileComplete] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!isLoading && !user) router.replace("/login");
  }, [user, isLoading, router]);

  useEffect(() => {
    if (!user) return;
    setPhone(user.phone ?? "");
    getPreferences().then(setPrefs).catch(() => {});
    getProfile().then(setProfile).catch(() => {});
    getFavorites()
      .then((f) => setSavedJobs(f.map((x) => x.job).filter(Boolean)))
      .catch(() => {});
    getMatchedJobs()
      .then((r) => {
        setMatchedJobs(r.jobs);
        setProfileComplete(r.profile_complete);
      })
      .catch(() => {});
  }, [user]);

  if (isLoading || !user) return null;

  const toggleList = (key: keyof UserPreferences, value: string) => {
    const list = prefs[key] as string[];
    setPrefs({
      ...prefs,
      [key]: list.includes(value) ? list.filter((v) => v !== value) : [...list, value],
    });
  };

  const saveProfile = async () => {
    setSaving(true);
    setMessage("");
    try {
      if (phone !== (user.phone ?? "")) {
        await updateMe({ phone: phone || undefined });
      }
      const updated = await updateProfile(profile);
      setProfile(updated);
      setProfileComplete(updated.profile_complete);
      const matched = await getMatchedJobs();
      setMatchedJobs(matched.jobs);
      setMessage("Profile saved! We'll suggest jobs that match your education and experience.");
    } catch {
      setMessage("Failed to save profile.");
    } finally {
      setSaving(false);
    }
  };

  const savePrefs = async () => {
    setSaving(true);
    setMessage("");
    try {
      await updatePreferences(prefs);
      setMessage("Alert preferences saved.");
    } catch {
      setMessage("Failed to save preferences.");
    } finally {
      setSaving(false);
    }
  };

  const addEducation = () => {
    setProfile({
      ...profile,
      education: [...profile.education, { degree: "", stream: "", year: undefined }],
    });
  };

  const addExperience = () => {
    setProfile({
      ...profile,
      experience: [...profile.experience, { role: "", organization: "", years: undefined }],
    });
  };

  const updateEducation = (index: number, field: keyof EducationEntry, value: string | number) => {
    const education = [...profile.education];
    education[index] = { ...education[index], [field]: value };
    setProfile({ ...profile, education });
  };

  const updateExperience = (index: number, field: keyof ExperienceEntry, value: string | number) => {
    const experience = [...profile.experience];
    experience[index] = { ...experience[index], [field]: value };
    setProfile({ ...profile, experience });
  };

  const tabs: { id: Tab; label: string; icon: typeof User }[] = [
    { id: "profile", label: "My Profile", icon: User },
    { id: "for-you", label: "Jobs For You", icon: Sparkles },
    { id: "alerts", label: "Alert Settings", icon: Bell },
    { id: "saved", label: "Saved Jobs", icon: Heart },
  ];

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">My Account</h1>
        <p className="mt-1 text-sm text-slate-500">
          Welcome, {user.name} · {user.email}
        </p>
        {user.is_admin && (
          <Link
            href="/admin"
            className="mt-3 inline-flex items-center gap-2 rounded-lg bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-900 ring-1 ring-amber-200 hover:bg-amber-100"
          >
            <Shield className="h-4 w-4" />
            Open Admin Panel
          </Link>
        )}
      </div>

      <div className="mb-6 flex flex-wrap gap-2 border-b border-slate-200">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-semibold transition ${
              tab === id
                ? "border-sky-700 text-sky-800"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {message && (
        <div className="mb-4 rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{message}</div>
      )}

      {tab === "profile" && (
        <div className="space-y-6">
          <div className="card-shadow rounded-xl border border-sky-100 bg-sky-50/50 p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-sky-900">Profile completeness</p>
                <p className="text-xs text-sky-700">
                  Complete your profile to get personalized job suggestions
                </p>
              </div>
              <p className="text-3xl font-black text-sky-800">
                {profile.stats?.completeness_percent ?? 0}%
              </p>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-sky-100">
              <div
                className="h-full rounded-full bg-sky-600 transition-all"
                style={{ width: `${profile.stats?.completeness_percent ?? 0}%` }}
              />
            </div>
          </div>

          <div className="card-shadow rounded-xl border border-slate-200 bg-white p-6">
            <h2 className="text-lg font-bold text-slate-900">Personal Details</h2>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <label className="block text-sm">
                <span className="font-medium text-slate-700">Phone (WhatsApp alerts)</span>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="10-digit mobile"
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                />
              </label>
              <label className="block text-sm">
                <span className="font-medium text-slate-700">Date of Birth</span>
                <input
                  type="date"
                  value={profile.date_of_birth?.slice(0, 10) ?? ""}
                  onChange={(e) => setProfile({ ...profile, date_of_birth: e.target.value || null })}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                />
              </label>
              <label className="block text-sm">
                <span className="font-medium text-slate-700">Gender</span>
                <select
                  value={profile.gender ?? ""}
                  onChange={(e) => setProfile({ ...profile, gender: e.target.value || null })}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                >
                  <option value="">Select</option>
                  {GENDERS.map((g) => (
                    <option key={g} value={g}>{g}</option>
                  ))}
                </select>
              </label>
              <label className="block text-sm">
                <span className="font-medium text-slate-700">Category</span>
                <select
                  value={profile.category ?? ""}
                  onChange={(e) => setProfile({ ...profile, category: e.target.value || null })}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                >
                  <option value="">Select</option>
                  {CATEGORIES_CANDIDATE.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </label>
              <label className="block text-sm sm:col-span-2">
                <span className="font-medium text-slate-700">Current State</span>
                <select
                  value={profile.current_state ?? ""}
                  onChange={(e) => setProfile({ ...profile, current_state: e.target.value || null })}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                >
                  <option value="">Select state</option>
                  {INDIAN_STATES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </label>
            </div>
          </div>

          <div className="card-shadow rounded-xl border border-slate-200 bg-white p-6">
            <div className="flex items-center gap-2">
              <GraduationCap className="h-5 w-5 text-violet-600" />
              <h2 className="text-lg font-bold text-slate-900">Education</h2>
            </div>
            <label className="mt-4 block text-sm">
              <span className="font-medium text-slate-700">Highest Qualification</span>
              <select
                value={profile.highest_qualification ?? ""}
                onChange={(e) =>
                  setProfile({ ...profile, highest_qualification: e.target.value || null })
                }
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
              >
                <option value="">Select</option>
                {QUALIFICATIONS.map((q) => (
                  <option key={q} value={q}>{q}</option>
                ))}
              </select>
            </label>
            {profile.education.map((edu, i) => (
              <div key={i} className="mt-4 grid gap-3 rounded-lg border border-slate-100 bg-slate-50 p-4 sm:grid-cols-2">
                <input
                  placeholder="Degree (e.g. B.Tech)"
                  value={edu.degree}
                  onChange={(e) => updateEducation(i, "degree", e.target.value)}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                />
                <input
                  placeholder="Stream / Subject"
                  value={edu.stream ?? ""}
                  onChange={(e) => updateEducation(i, "stream", e.target.value)}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                />
                <input
                  placeholder="Board / University"
                  value={edu.board_university ?? ""}
                  onChange={(e) => updateEducation(i, "board_university", e.target.value)}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                />
                <input
                  type="number"
                  placeholder="Year"
                  value={edu.year ?? ""}
                  onChange={(e) => updateEducation(i, "year", Number(e.target.value))}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                />
              </div>
            ))}
            <button type="button" onClick={addEducation} className="mt-3 text-sm font-semibold text-sky-700">
              + Add education
            </button>
          </div>

          <div className="card-shadow rounded-xl border border-slate-200 bg-white p-6">
            <div className="flex items-center gap-2">
              <Briefcase className="h-5 w-5 text-amber-600" />
              <h2 className="text-lg font-bold text-slate-900">Experience</h2>
            </div>
            <label className="mt-4 block text-sm">
              <span className="font-medium text-slate-700">Total Experience (years)</span>
              <input
                type="number"
                min={0}
                step={0.5}
                value={profile.experience_years ?? ""}
                onChange={(e) =>
                  setProfile({
                    ...profile,
                    experience_years: e.target.value ? Number(e.target.value) : null,
                  })
                }
                className="mt-1 w-full max-w-xs rounded-lg border border-slate-200 px-3 py-2"
              />
            </label>
            {profile.experience.map((exp, i) => (
              <div key={i} className="mt-4 grid gap-3 rounded-lg border border-slate-100 bg-slate-50 p-4 sm:grid-cols-2">
                <input
                  placeholder="Role / Designation"
                  value={exp.role}
                  onChange={(e) => updateExperience(i, "role", e.target.value)}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                />
                <input
                  placeholder="Organization"
                  value={exp.organization ?? ""}
                  onChange={(e) => updateExperience(i, "organization", e.target.value)}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                />
                <input
                  type="number"
                  placeholder="Years in role"
                  value={exp.years ?? ""}
                  onChange={(e) => updateExperience(i, "years", Number(e.target.value))}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                />
                <input
                  placeholder="Domain (e.g. Teaching, IT)"
                  value={exp.domain ?? ""}
                  onChange={(e) => updateExperience(i, "domain", e.target.value)}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                />
              </div>
            ))}
            <button type="button" onClick={addExperience} className="mt-3 text-sm font-semibold text-sky-700">
              + Add experience
            </button>
          </div>

          <div className="card-shadow rounded-xl border border-slate-200 bg-white p-6">
            <h2 className="text-lg font-bold text-slate-900">Job Preferences</h2>
            <label className="mt-4 block text-sm">
              <span className="font-medium text-slate-700">Preferred Posts (comma separated)</span>
              <input
                value={profile.preferred_posts.join(", ")}
                onChange={(e) =>
                  setProfile({
                    ...profile,
                    preferred_posts: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
                  })
                }
                placeholder="Clerk, Teacher, Assistant, Engineer"
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
              />
            </label>
            <label className="mt-4 block text-sm">
              <span className="font-medium text-slate-700">Skills (comma separated)</span>
              <input
                value={profile.skills.join(", ")}
                onChange={(e) =>
                  setProfile({
                    ...profile,
                    skills: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
                  })
                }
                placeholder="Excel, Teaching, Accounting"
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
              />
            </label>
          </div>

          <button
            type="button"
            onClick={saveProfile}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-lg bg-sky-700 px-6 py-3 text-sm font-bold text-white hover:bg-sky-800 disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            {saving ? "Saving..." : "Save profile"}
          </button>
        </div>
      )}

      {tab === "for-you" && (
        <div>
          {!profileComplete && (
            <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              Complete your profile (qualification, state, experience) to unlock personalized job matches.
              <button type="button" onClick={() => setTab("profile")} className="ml-2 font-semibold underline">
                Go to profile
              </button>
            </div>
          )}
          {matchedJobs.length > 0 ? (
            <div className="space-y-4">
              {matchedJobs.map(({ job, match_score, match_reasons }) => (
                <div key={job.id} className="card-shadow rounded-xl border border-slate-200 bg-white p-4">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-bold text-emerald-800">
                      {match_score}% match
                    </span>
                    {match_reasons[0] && (
                      <span className="text-xs text-slate-500">{match_reasons[0]}</span>
                    )}
                  </div>
                  <JobList jobs={[job]} />
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-slate-300 bg-white py-16 text-center">
              <Sparkles className="mx-auto h-10 w-10 text-slate-300" />
              <p className="mt-3 font-medium text-slate-600">No personalized matches yet</p>
              <p className="mt-1 text-sm text-slate-400">Complete your profile and check back after new notifications</p>
            </div>
          )}
        </div>
      )}

      {tab === "alerts" && (
        <div className="space-y-6">
          <div className="card-shadow rounded-xl border border-slate-200 bg-white p-6">
            <h2 className="text-lg font-bold text-slate-900">Notification Channels</h2>
            <div className="mt-4 space-y-3">
              <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-slate-100 p-4 hover:bg-slate-50">
                <input
                  type="checkbox"
                  checked={prefs.email_alerts}
                  onChange={(e) => setPrefs({ ...prefs, email_alerts: e.target.checked })}
                  className="h-4 w-4 rounded border-slate-300 text-sky-700"
                />
                <Mail className="h-5 w-5 text-sky-600" />
                <div>
                  <p className="font-semibold text-slate-800">Email alerts</p>
                  <p className="text-xs text-slate-500">Personalized matches sent to {user.email}</p>
                </div>
              </label>
              <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-slate-100 p-4 hover:bg-slate-50">
                <input
                  type="checkbox"
                  checked={prefs.whatsapp_alerts}
                  onChange={(e) => setPrefs({ ...prefs, whatsapp_alerts: e.target.checked })}
                  className="h-4 w-4 rounded border-slate-300 text-sky-700"
                />
                <MessageCircle className="h-5 w-5 text-emerald-600" />
                <div>
                  <p className="font-semibold text-slate-800">WhatsApp alerts</p>
                  <p className="text-xs text-slate-500">
                    {phone ? `Sent to +91${phone}` : "Add phone in Profile tab"}
                  </p>
                </div>
              </label>
            </div>
          </div>

          <div className="card-shadow rounded-xl border border-slate-200 bg-white p-6">
            <h2 className="text-lg font-bold text-slate-900">Preferred States</h2>
            <div className="mt-4 flex flex-wrap gap-2">
              {INDIAN_STATES.slice(0, 16).map((state) => (
                <button
                  key={state}
                  type="button"
                  onClick={() => toggleList("states", state)}
                  className={`rounded-full px-3 py-1.5 text-xs font-medium transition ${
                    prefs.states.includes(state)
                      ? "bg-sky-700 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {state}
                </button>
              ))}
            </div>
          </div>

          <div className="card-shadow rounded-xl border border-slate-200 bg-white p-6">
            <h2 className="text-lg font-bold text-slate-900">Qualification filters</h2>
            <div className="mt-4 flex flex-wrap gap-2">
              {QUALIFICATIONS.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => toggleList("qualifications", q)}
                  className={`rounded-full px-3 py-1.5 text-xs font-medium transition ${
                    prefs.qualifications.includes(q)
                      ? "bg-sky-700 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          <button
            type="button"
            onClick={savePrefs}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-lg bg-sky-700 px-6 py-3 text-sm font-bold text-white hover:bg-sky-800 disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            {saving ? "Saving..." : "Save alert preferences"}
          </button>
        </div>
      )}

      {tab === "saved" && (
        <div>
          {savedJobs.length > 0 ? (
            <JobList jobs={savedJobs} />
          ) : (
            <div className="rounded-xl border border-dashed border-slate-300 bg-white py-16 text-center">
              <Heart className="mx-auto h-10 w-10 text-slate-300" />
              <p className="mt-3 font-medium text-slate-600">No saved jobs yet</p>
              <Link href="/jobs/notification" className="mt-4 inline-block text-sm font-semibold text-sky-700 hover:underline">
                Browse jobs →
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

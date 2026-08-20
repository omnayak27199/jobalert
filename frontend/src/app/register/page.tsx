"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/components/AuthProvider";

export default function RegisterPage() {
  const { register, user } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({
    name: "",
    email: "",
    phone: "",
    password: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (user) {
    router.replace("/account");
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register({
        name: form.name,
        email: form.email,
        password: form.password,
        phone: form.phone || undefined,
      });
      router.push("/account");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-md flex-col justify-center px-4 py-12">
      <div className="card-shadow rounded-2xl border border-slate-200 bg-white p-8">
        <h1 className="text-2xl font-bold text-slate-900">Create account</h1>
        <p className="mt-1 text-sm text-slate-500">
          Get email &amp; WhatsApp alerts for jobs matching your preferences
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          {error && (
            <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}
          {[
            { key: "name", label: "Full name", type: "text" },
            { key: "email", label: "Email", type: "email" },
            { key: "phone", label: "Phone (for WhatsApp alerts)", type: "tel" },
            { key: "password", label: "Password (min 6 chars)", type: "password" },
          ].map(({ key, label, type }) => (
            <div key={key}>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                {label}
              </label>
              <input
                type={type}
                required={key !== "phone"}
                minLength={key === "password" ? 6 : undefined}
                value={form[key as keyof typeof form]}
                onChange={(e) =>
                  setForm({ ...form, [key]: e.target.value })
                }
                className="w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm focus:border-sky-300 focus:outline-none focus:ring-2 focus:ring-sky-100"
              />
            </div>
          ))}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-sky-700 py-3 text-sm font-bold text-white hover:bg-sky-800 disabled:opacity-50"
          >
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-500">
          Already have an account?{" "}
          <Link href="/login" className="font-semibold text-sky-700 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

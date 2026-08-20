"use client";

import { Heart } from "lucide-react";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { addFavorite, checkFavorite, removeFavorite } from "@/lib/auth";
import { cn } from "@/lib/utils";

interface FavoriteButtonProps {
  jobId: number;
  className?: string;
}

export function FavoriteButton({ jobId, className }: FavoriteButtonProps) {
  const { user } = useAuth();
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!user) return;
    checkFavorite(jobId)
      .then((r) => setSaved(r.saved))
      .catch(() => {});
  }, [user, jobId]);

  if (!user) return null;

  const toggle = async () => {
    setLoading(true);
    try {
      if (saved) {
        await removeFavorite(jobId);
        setSaved(false);
      } else {
        await addFavorite(jobId);
        setSaved(true);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={loading}
      title={saved ? "Remove from saved" : "Save job"}
      className={cn(
        "inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium transition",
        saved
          ? "bg-rose-50 text-rose-700 ring-1 ring-rose-200"
          : "bg-slate-50 text-slate-500 hover:bg-rose-50 hover:text-rose-600",
        className
      )}
    >
      <Heart className={cn("h-3.5 w-3.5", saved && "fill-current")} />
      {saved ? "Saved" : "Save"}
    </button>
  );
}

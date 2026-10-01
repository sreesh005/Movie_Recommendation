import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

const STORAGE_KEY = "later.ratings";
const MIN_RATINGS = 8;

type RatingsContextValue = {
  ratings: Record<number, number>;
  setRating: (movieId: number, rating: number) => void;
  clearRatings: () => void;
  count: number;
  readyForRecs: boolean;
  mood: string;
  setMood: (mood: string) => void;
};

const RatingsContext = createContext<RatingsContextValue | null>(null);

function loadRatings(): Record<number, number> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Record<string, number>;
    const out: Record<number, number> = {};
    for (const [k, v] of Object.entries(parsed)) {
      const id = Number(k);
      const rating = Number(v);
      if (id && rating >= 0.5 && rating <= 5) out[id] = rating;
    }
    return out;
  } catch {
    return {};
  }
}

export function RatingsProvider({ children }: { children: ReactNode }) {
  const [ratings, setRatings] = useState<Record<number, number>>(loadRatings);
  const [mood, setMood] = useState("tonight");

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ratings));
  }, [ratings]);

  const value = useMemo<RatingsContextValue>(
    () => ({
      ratings,
      setRating: (movieId, rating) => {
        setRatings((prev) => {
          const next = { ...prev };
          if (rating <= 0) delete next[movieId];
          else next[movieId] = rating;
          return next;
        });
      },
      clearRatings: () => setRatings({}),
      count: Object.keys(ratings).length,
      readyForRecs: Object.keys(ratings).length >= MIN_RATINGS,
      mood,
      setMood,
    }),
    [ratings, mood]
  );

  return <RatingsContext.Provider value={value}>{children}</RatingsContext.Provider>;
}

export function useRatings() {
  const ctx = useContext(RatingsContext);
  if (!ctx) throw new Error("useRatings must be used within RatingsProvider");
  return ctx;
}

export { MIN_RATINGS };

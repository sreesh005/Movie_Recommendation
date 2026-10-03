import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

const STORAGE_KEY = "later.ratings";
const PASSED_KEY = "later.passed";
const MIN_RATINGS = 8;

type RatingsContextValue = {
  ratings: Record<number, number>;
  setRating: (movieId: number, rating: number) => void;
  clearRatings: () => void;
  count: number;
  readyForRecs: boolean;
  mood: string;
  setMood: (mood: string) => void;
  passed: Record<number, true>;
  togglePass: (movieId: number) => void;
  isPassed: (movieId: number) => boolean;
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

function loadPassed(): Record<number, true> {
  try {
    const raw = localStorage.getItem(PASSED_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as number[];
    const out: Record<number, true> = {};
    for (const id of parsed) {
      const n = Number(id);
      if (n) out[n] = true;
    }
    return out;
  } catch {
    return {};
  }
}

export function RatingsProvider({ children }: { children: ReactNode }) {
  const [ratings, setRatings] = useState<Record<number, number>>(loadRatings);
  const [passed, setPassed] = useState<Record<number, true>>(loadPassed);
  const [mood, setMood] = useState("tonight");

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ratings));
  }, [ratings]);

  useEffect(() => {
    localStorage.setItem(PASSED_KEY, JSON.stringify(Object.keys(passed).map(Number)));
  }, [passed]);

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
        if (rating > 0) {
          setPassed((prev) => {
            if (!prev[movieId]) return prev;
            const next = { ...prev };
            delete next[movieId];
            return next;
          });
        }
      },
      clearRatings: () => setRatings({}),
      count: Object.keys(ratings).length,
      readyForRecs: Object.keys(ratings).length >= MIN_RATINGS,
      mood,
      setMood,
      passed,
      togglePass: (movieId) => {
        setPassed((prev) => {
          const next = { ...prev };
          if (next[movieId]) delete next[movieId];
          else next[movieId] = true;
          return next;
        });
      },
      isPassed: (movieId) => Boolean(passed[movieId]),
    }),
    [ratings, mood, passed]
  );

  return <RatingsContext.Provider value={value}>{children}</RatingsContext.Provider>;
}

export function useRatings() {
  const ctx = useContext(RatingsContext);
  if (!ctx) throw new Error("useRatings must be used within RatingsProvider");
  return ctx;
}

export { MIN_RATINGS };

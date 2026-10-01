import type { Movie, RecommendResponse } from "./types";

async function readJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export function fetchStarters() {
  return fetch("/api/starters").then((r) => readJson<Movie[]>(r));
}

export function searchMovies(q: string) {
  return fetch(`/api/search?q=${encodeURIComponent(q)}`).then((r) => readJson<Movie[]>(r));
}

export function fetchMovie(id: number) {
  return fetch(`/api/movies/${id}`).then((r) => readJson<Movie>(r));
}

export function fetchRecommend(body: {
  ratings: Record<number, number>;
  mood: string | null;
  n?: number;
}) {
  const now = new Date();
  return fetch("/api/recommend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ratings: body.ratings,
      mood: body.mood,
      hour: now.getHours(),
      weekday: (now.getDay() + 6) % 7,
      n: body.n ?? 40,
    }),
  }).then((r) => readJson<RecommendResponse>(r));
}

export function fetchHealth() {
  return fetch("/api/health").then((r) =>
    readJson<{ ready: boolean; error: string | null; movies: number }>(r)
  );
}

export function fetchMetrics() {
  return fetch("/api/metrics").then((r) => readJson<Record<string, string | number>>(r));
}

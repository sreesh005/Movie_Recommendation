import type { Movie, RecommendResponse } from "./types";

async function readJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export function fetchSurvey() {
  return fetch("/api/survey").then((r) => readJson<{ name: string; movies: Movie[] }[]>(r));
}

export function searchMovies(q: string) {
  return fetch(`/api/search?q=${encodeURIComponent(q)}`).then((r) => readJson<Movie[]>(r));
}

export function fetchMovie(id: number) {
  return fetch(`/api/movies/${id}`).then((r) => readJson<Movie>(r));
}

export function fetchMovieBatch(ids: number[]) {
  return fetch("/api/movies/batch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids }),
  }).then((r) => readJson<Movie[]>(r));
}

export function fetchRecommend(body: {
  ratings: Record<number, number>;
  mood: string | null;
  language?: string | null;
  notInterested?: number[];
  n?: number;
}) {
  const now = new Date();
  return fetch("/api/recommend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ratings: body.ratings,
      mood: body.mood,
      language: body.language || null,
      not_interested: body.notInterested ?? [],
      hour: now.getHours(),
      weekday: (now.getDay() + 6) % 7,
      n: body.n ?? 80,
    }),
  }).then((r) => readJson<RecommendResponse>(r));
}

export function fetchForeignLanguages() {
  return fetch("/api/foreign-languages").then((r) => readJson<{ id: string; count: number }[]>(r));
}

export function fetchGenres() {
  return fetch("/api/genres").then((r) => readJson<{ id: string; count: number }[]>(r));
}

export function fetchBrowse(genre?: string | null, q = "") {
  const params = new URLSearchParams();
  if (genre) params.set("genre", genre);
  if (q) params.set("q", q);
  params.set("limit", "60");
  return fetch(`/api/browse?${params.toString()}`).then((r) =>
    readJson<{ genre: string | null; total: number; movies: Movie[] }>(r)
  );
}

export function fetchHealth() {
  return fetch("/api/health").then((r) =>
    readJson<{ ready: boolean; error: string | null; movies: number }>(r)
  );
}

export function fetchMetrics() {
  return fetch("/api/metrics").then((r) => readJson<Record<string, string | number>>(r));
}

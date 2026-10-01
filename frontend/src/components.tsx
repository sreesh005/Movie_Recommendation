import { useState } from "react";
import type { Movie } from "./types";

const PALETTES = [
  ["#3a2a1c", "#c9a227"],
  ["#1e2a28", "#d7c4a3"],
  ["#2a1c22", "#e0b080"],
  ["#1c2430", "#cfc3a8"],
  ["#2d2416", "#f0d9a8"],
  ["#241c18", "#b08968"],
];

function palette(id: number) {
  return PALETTES[Math.abs(id) % PALETTES.length];
}

export function Poster({ movie, large = false }: { movie: Movie; large?: boolean }) {
  const [failed, setFailed] = useState(false);
  const [bg, ink] = palette(movie.movie_id);
  if (movie.poster_url && !failed) {
    return (
      <div className="poster poster-photo" style={{ minHeight: large ? 320 : undefined }}>
        <img src={movie.poster_url} alt={movie.title} onError={() => setFailed(true)} />
      </div>
    );
  }
  return (
    <div
      className="poster"
      style={{ background: bg, color: ink, minHeight: large ? 320 : undefined }}
    >
      <b>{movie.title}</b>
      <small>{movie.year ?? "Film"}</small>
    </div>
  );
}

export function Stars({
  value,
  onChange,
}: {
  value: number;
  onChange?: (value: number) => void;
}) {
  return (
    <div className="stars" onClick={(e) => e.stopPropagation()}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          className={n <= Math.round(value) ? "on" : ""}
          aria-label={`${n} star`}
          onClick={() => onChange?.(n === Math.round(value) ? 0 : n)}
        >
          ★
        </button>
      ))}
    </div>
  );
}

export function MovieCard({
  movie,
  rating,
  onOpen,
  onRate,
  subtitle,
}: {
  movie: Movie;
  rating?: number;
  onOpen: (id: number) => void;
  onRate?: (id: number, rating: number) => void;
  subtitle?: string;
}) {
  return (
    <button className="card" type="button" onClick={() => onOpen(movie.movie_id)}>
      <Poster movie={movie} />
      <div className="card-meta">
        <div className="title">
          {movie.title}
          {movie.year ? ` (${movie.year})` : ""}
        </div>
        <div className="sub">{subtitle ?? movie.genres.slice(0, 2).join(" · ")}</div>
        {onRate ? <Stars value={rating ?? 0} onChange={(v) => onRate(movie.movie_id, v)} /> : null}
      </div>
    </button>
  );
}

export function MovieRow({
  movies,
  ratings,
  onOpen,
  onRate,
  subtitleFor,
}: {
  movies: Movie[];
  ratings?: Record<number, number>;
  onOpen: (id: number) => void;
  onRate?: (id: number, rating: number) => void;
  subtitleFor?: (movie: Movie) => string;
}) {
  return (
    <div className="row">
      {movies.map((movie) => (
        <MovieCard
          key={movie.movie_id}
          movie={movie}
          rating={ratings?.[movie.movie_id]}
          onOpen={onOpen}
          onRate={onRate}
          subtitle={subtitleFor?.(movie)}
        />
      ))}
    </div>
  );
}

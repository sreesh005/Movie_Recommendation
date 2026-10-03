import { useState } from "react";
import type { Movie } from "./types";
import { useRatings } from "./state";

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
  const pick = (next: number) => onChange?.(next === value ? 0 : next);
  return (
    <div className="stars" onClick={(e) => e.stopPropagation()}>
      {[1, 2, 3, 4, 5].map((n) => {
        const fill = value >= n ? "full" : value >= n - 0.5 ? "half" : "";
        return (
          <span key={n} className="star">
            <span className={`star-face ${fill}`} aria-hidden>
              ★
            </span>
            <button type="button" className="star-hit left" aria-label={`${n - 0.5} stars`} onClick={() => pick(n - 0.5)} />
            <button type="button" className="star-hit right" aria-label={`${n} stars`} onClick={() => pick(n)} />
          </span>
        );
      })}
    </div>
  );
}

export function MovieCard({
  movie,
  rating,
  onOpen,
  onRate,
  subtitle,
  showPass = true,
}: {
  movie: Movie;
  rating?: number;
  onOpen: (id: number) => void;
  onRate?: (id: number, rating: number) => void;
  subtitle?: string;
  showPass?: boolean;
}) {
  const { togglePass, isPassed } = useRatings();
  const hidden = isPassed(movie.movie_id);
  return (
    <div className={`card ${hidden ? "passed" : ""}`}>
      <div className="poster-wrap">
        <button className="poster-hit" type="button" onClick={() => onOpen(movie.movie_id)}>
          <Poster movie={movie} />
        </button>
        {showPass ? (
          <button
            className={`pass-x ${hidden ? "on" : ""}`}
            type="button"
            title={hidden ? "Show this again" : "Not interested"}
            aria-label={hidden ? "Show this again" : "Not interested"}
            onClick={() => togglePass(movie.movie_id)}
          >
            {hidden ? "↩" : "✕"}
          </button>
        ) : null}
      </div>
      <div className="card-meta">
        <button className="title-hit" type="button" onClick={() => onOpen(movie.movie_id)}>
          {movie.title}
          {movie.year ? ` (${movie.year})` : ""}
        </button>
        <div className="sub">{subtitle ?? movie.genres.slice(0, 2).join(" · ")}</div>
        {onRate ? <Stars value={rating ?? 0} onChange={(v) => onRate(movie.movie_id, v)} /> : null}
      </div>
    </div>
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

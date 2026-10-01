import { useEffect, useMemo, useState } from "react";
import { fetchHealth, fetchMovie, fetchMetrics, fetchRecommend, fetchStarters, searchMovies } from "./api";
import { MovieCard, MovieRow, Poster, Stars } from "./components";
import { MIN_RATINGS, useRatings } from "./state";
import type { Movie, RecMovie, RecommendResponse, View } from "./types";

const MOODS = [
  { id: "tonight", label: "Tonight" },
  { id: "date", label: "Date night" },
  { id: "family", label: "Family" },
  { id: "scary", label: "Scary" },
  { id: "comfort", label: "Comfort" },
  { id: "thrills", label: "Thrills" },
];

export default function App() {
  const [view, setView] = useState<View>({ name: "tonight" });
  const [health, setHealth] = useState<{ ready: boolean; error: string | null } | null>(null);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => setHealth({ ready: false, error: "Cannot reach the Later API. Start the backend." }));
  }, []);

  const open = (id: number) => setView({ name: "movie", id });

  return (
    <div className="shell">
      <header className="topbar">
        <button className="brand" onClick={() => setView({ name: "tonight" })}>
          <strong>Later</strong>
          <span>What to watch, and when</span>
        </button>
        <nav className="nav">
          <button className={view.name === "tonight" ? "active" : ""} onClick={() => setView({ name: "tonight" })}>
            Tonight
          </button>
          <button className={view.name === "rate" ? "active" : ""} onClick={() => setView({ name: "rate" })}>
            Rate
          </button>
          <button className={view.name === "foryou" ? "active" : ""} onClick={() => setView({ name: "foryou" })}>
            For you
          </button>
        </nav>
      </header>

      {!health ? <p className="status">Loading…</p> : null}
      {health && !health.ready ? (
        <p className="status">{health.error || "Train the model first: python -m backend.train"}</p>
      ) : null}

      {health?.ready && view.name === "tonight" ? <Tonight onOpen={open} onRate={() => setView({ name: "rate" })} /> : null}
      {health?.ready && view.name === "rate" ? <Rate onOpen={open} /> : null}
      {health?.ready && view.name === "foryou" ? <ForYou onOpen={open} onRate={() => setView({ name: "rate" })} /> : null}
      {health?.ready && view.name === "movie" ? (
        <MoviePage id={view.id} onOpen={open} onBack={() => setView({ name: "tonight" })} />
      ) : null}
    </div>
  );
}

function useRecs() {
  const { ratings, mood, readyForRecs } = useRatings();
  const [data, setData] = useState<RecommendResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const key = useMemo(() => JSON.stringify({ ratings, mood }), [ratings, mood]);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    fetchRecommend({ ratings, mood })
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [key, ratings, mood]);

  return { data, error, readyForRecs };
}

function Tonight({ onOpen, onRate }: { onOpen: (id: number) => void; onRate: () => void }) {
  const { mood, setMood, count } = useRatings();
  const { data, error, readyForRecs } = useRecs();
  const hero = data?.hero;

  return (
    <div>
      {!readyForRecs ? (
        <div className="banner" style={{ marginTop: 24 }}>
          <div>
            Rate {MIN_RATINGS} films you know so Later can pick a night for you. {count}/{MIN_RATINGS} so far.
          </div>
          <button className="primary" onClick={onRate}>
            Rate movies
          </button>
        </div>
      ) : null}

      {error ? <p className="status">{error}</p> : null}

      {hero ? (
        <section className="hero">
          <button className="card" type="button" onClick={() => onOpen(hero.movie_id)}>
            <Poster movie={hero} large />
          </button>
          <div>
            <div className="watch-pill">
              <span>When to watch</span>
              <b>
                {hero.watch.slot} · {hero.watch.when}
              </b>
            </div>
            <h1>{hero.title}</h1>
            <p className="lead">
              {hero.reason}. {hero.watch.detail}
            </p>
            <p className="lead" style={{ marginTop: -8 }}>
              Predicted {hero.predicted_rating.toFixed(1)} / 5 · {hero.genres.slice(0, 3).join(" · ")}
            </p>
            <div className="moods">
              {MOODS.map((item) => (
                <button key={item.id} className={mood === item.id ? "on" : ""} onClick={() => setMood(item.id)}>
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        </section>
      ) : (
        <p className="status">Finding tonight’s pick…</p>
      )}

      {data?.tonight?.length ? (
        <section className="section">
          <h2>Fits this hour</h2>
          <MovieRow
            movies={data.tonight}
            onOpen={onOpen}
            subtitleFor={(m) => `${(m as RecMovie).watch.slot} · ${(m as RecMovie).watch.when}`}
          />
        </section>
      ) : null}

      {data?.top?.length ? (
        <section className="section">
          <h2>More like that</h2>
          <MovieRow movies={data.top.slice(1, 13)} onOpen={onOpen} />
        </section>
      ) : null}

      <About />
    </div>
  );
}

function Rate({ onOpen }: { onOpen: (id: number) => void }) {
  const { ratings, setRating, count, clearRatings } = useRatings();
  const [starters, setStarters] = useState<Movie[]>([]);
  const [hits, setHits] = useState<Movie[] | null>(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    fetchStarters().then(setStarters).catch(() => setStarters([]));
  }, []);

  useEffect(() => {
    if (!q.trim()) {
      setHits(null);
      return;
    }
    const handle = window.setTimeout(() => {
      searchMovies(q).then(setHits).catch(() => setHits([]));
    }, 180);
    return () => window.clearTimeout(handle);
  }, [q]);

  const movies = hits ?? starters;

  return (
    <div>
      <section className="hero" style={{ gridTemplateColumns: "1fr" }}>
        <div>
          <h1>Rate what you know.</h1>
          <p className="lead">
            Click stars on posters you remember. {count} rated
            {count >= MIN_RATINGS ? " — enough to personalize." : ` — ${Math.max(0, MIN_RATINGS - count)} more to unlock For you.`}
          </p>
          <input
            className="search"
            placeholder="Search the catalog — inception, spirited away, heat…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          {count > 0 ? (
            <button className="ghost" style={{ marginTop: 14 }} onClick={clearRatings}>
              Clear my ratings
            </button>
          ) : null}
        </div>
      </section>
      <div className="grid">
        {movies.map((movie) => (
          <MovieCard
            key={movie.movie_id}
            movie={movie}
            rating={ratings[movie.movie_id]}
            onOpen={onOpen}
            onRate={setRating}
          />
        ))}
      </div>
    </div>
  );
}

function ForYou({ onOpen, onRate }: { onOpen: (id: number) => void; onRate: () => void }) {
  const { mood, setMood, readyForRecs } = useRatings();
  const { data, error } = useRecs();

  if (!readyForRecs) {
    return (
      <div className="banner" style={{ marginTop: 32 }}>
        <div>For you fills in after {MIN_RATINGS} ratings. That is how we avoid cold-start junk.</div>
        <button className="primary" onClick={onRate}>
          Rate movies
        </button>
      </div>
    );
  }

  return (
    <div>
      <section className="hero" style={{ gridTemplateColumns: "1fr" }}>
        <div>
          <h1>For you</h1>
          <p className="lead">
            LensKit item–item collaborative filtering, blended with genre taste and a popularity prior.
          </p>
          <div className="moods">
            {MOODS.map((item) => (
              <button key={item.id} className={mood === item.id ? "on" : ""} onClick={() => setMood(item.id)}>
                {item.label}
              </button>
            ))}
          </div>
        </div>
      </section>
      {error ? <p className="status">{error}</p> : null}
      {data?.top ? (
        <section className="section">
          <h2>Top picks</h2>
          <MovieRow
            movies={data.top}
            onOpen={onOpen}
            subtitleFor={(m) => `${(m as RecMovie).predicted_rating.toFixed(1)} predicted · ${(m as RecMovie).reason}`}
          />
        </section>
      ) : null}
      {data?.because?.map((row) => (
        <section className="section" key={row.title}>
          <h2>Because you liked {row.title}</h2>
          <MovieRow movies={row.movies} onOpen={onOpen} />
        </section>
      ))}
      {data?.hidden?.length ? (
        <section className="section">
          <h2>Quieter titles in your taste</h2>
          <MovieRow movies={data.hidden} onOpen={onOpen} />
        </section>
      ) : null}
    </div>
  );
}

function MoviePage({
  id,
  onOpen,
  onBack,
}: {
  id: number;
  onOpen: (id: number) => void;
  onBack: () => void;
}) {
  const { ratings, setRating } = useRatings();
  const [movie, setMovie] = useState<Movie | null>(null);
  const { data } = useRecs();

  useEffect(() => {
    fetchMovie(id).then(setMovie).catch(() => setMovie(null));
  }, [id]);

  if (!movie) return <p className="status">Loading title…</p>;

  const similar = (data?.top || []).filter((m) => m.movie_id !== id).slice(0, 10);

  return (
    <div>
      <button className="ghost" style={{ marginTop: 20 }} onClick={onBack}>
        Back
      </button>
      <section className="detail">
        <Poster movie={movie} large />
        <div>
          <h1>{movie.title}</h1>
          <div className="meta-line">
            {[movie.year, movie.genres.join(" · "), `${movie.avg_rating.toFixed(1)} avg from ${movie.rating_count.toLocaleString()} ratings`]
              .filter(Boolean)
              .join("  ·  ")}
          </div>
          <Stars value={ratings[movie.movie_id] ?? 0} onChange={(v) => setRating(movie.movie_id, v)} />
          <div className="watch-card">
            <h3>When to watch</h3>
            <p style={{ margin: "0 0 8px", fontFamily: "var(--serif)", fontSize: 28 }}>
              {movie.watch.slot}, {movie.watch.when.toLowerCase()}
            </p>
            <p style={{ margin: 0, color: "var(--muted)" }}>{movie.watch.detail}</p>
          </div>
          {movie.tags.length ? (
            <div className="tags">
              {movie.tags.map((tag) => (
                <span key={tag}>{tag}</span>
              ))}
            </div>
          ) : null}
          <p className="lead">
            {movie.imdb_id ? (
              <a href={`https://www.imdb.com/title/tt${movie.imdb_id}/`} target="_blank" rel="noreferrer">
                IMDb
              </a>
            ) : null}
            {movie.imdb_id && movie.tmdb_id ? "  ·  " : null}
            {movie.tmdb_id ? (
              <a href={`https://www.themoviedb.org/movie/${movie.tmdb_id}`} target="_blank" rel="noreferrer">
                TMDB
              </a>
            ) : null}
          </p>
        </div>
      </section>
      {similar.length ? (
        <section className="section">
          <h2>You might watch next</h2>
          <MovieRow movies={similar} onOpen={onOpen} />
        </section>
      ) : null}
    </div>
  );
}

function About() {
  const [metrics, setMetrics] = useState<Record<string, string | number> | null>(null);
  useEffect(() => {
    fetchMetrics().then(setMetrics).catch(() => setMetrics(null));
  }, []);
  if (!metrics) return null;
  return (
    <aside className="about">
      Later is trained on a filtered slice of MovieLens 32M with LensKit item–item CF (Harper & Konstan 2015;
      Ekstrand 2020). Holdout {String(metrics.users_evaluated)} users: recall@20 {String(metrics.recall_at_20)}, nDCG@20{" "}
      {String(metrics.ndcg_at_20)}. Watch windows use rating timestamps converted to America/Chicago, plus genre rules.
      Posters from TMDB; this product uses the TMDB API but is not endorsed or certified by TMDB.
    </aside>
  );
}

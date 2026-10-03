import { useEffect, useMemo, useRef, useState } from "react";
import {
  fetchBrowse,
  fetchForeignLanguages,
  fetchGenres,
  fetchHealth,
  fetchMovie,
  fetchMovieBatch,
  fetchMetrics,
  fetchRecommend,
  fetchSurvey,
  searchMovies,
} from "./api";
import { MovieCard, MovieRow, Poster, Stars } from "./components";
import { MIN_RATINGS, useRatings } from "./state";
import type { Movie, RecMovie, RecommendResponse, View } from "./types";

const MOODS = [
  { id: "indie", label: "Indie" },
  { id: "niche", label: "Niche" },
  { id: "foreign", label: "Foreign" },
  { id: "tonight", label: "Tonight" },
  { id: "date", label: "Date night" },
  { id: "family", label: "Family" },
  { id: "scary", label: "Scary" },
  { id: "comfort", label: "Comfort" },
  { id: "thrills", label: "Thrills" },
];

const MOOD_ROW: Record<string, string> = {
  easy: "Turn your brain off",
  focus: "Pay attention",
  indie: "Indie",
  niche: "Niche",
  foreign: "Foreign",
  tonight: "Right for this hour",
  date: "Date night",
  family: "Family watch",
  scary: "Scary",
  comfort: "Comfort",
  thrills: "Thrills",
};

const ENERGY = [
  { id: "easy", title: "Turn your brain off", detail: "Laid-back. Easy company. No homework." },
  { id: "focus", title: "Pay attention", detail: "Sit with it. Twists, talk, and no half-watching." },
];

function listFrom(view: View): Exclude<View, { name: "movie"; id: number }> {
  return view.name === "movie" ? { name: "survey" } : view;
}

function withoutPassed<T extends { movie_id: number }>(movies: T[] | undefined, passed: Record<number, true>) {
  return (movies ?? []).filter((movie) => !passed[movie.movie_id]);
}

function PassButton({ movieId }: { movieId: number }) {
  const { togglePass, isPassed } = useRatings();
  const hidden = isPassed(movieId);
  return (
    <button type="button" className={`ghost pass-btn ${hidden ? "on" : ""}`} onClick={() => togglePass(movieId)}>
      {hidden ? "Show this again" : "Not interested"}
    </button>
  );
}

export default function App() {
  const { readyForRecs } = useRatings();
  const initial: Exclude<View, { name: "movie"; id: number }> = readyForRecs ? { name: "home" } : { name: "survey" };
  const [view, setView] = useState<View>(initial);
  const [listView, setListView] = useState<Exclude<View, { name: "movie"; id: number }>>(initial);
  const [keepHome, setKeepHome] = useState(readyForRecs);
  const [keepBrowse, setKeepBrowse] = useState(false);
  const [keepLibrary, setKeepLibrary] = useState(false);
  const [health, setHealth] = useState<{ ready: boolean; error: string | null } | null>(null);
  const [query, setQuery] = useState("");
  const listScroll = useRef(0);

  const go = (next: View) => {
    if (next.name === "movie") {
      if (view.name !== "movie") {
        setListView(view);
        listScroll.current = window.scrollY;
      }
      setView(next);
      window.scrollTo(0, 0);
      return;
    }
    const restore = view.name === "movie";
    const returningTo = listView.name;
    setListView(next);
    setView(next);
    window.setTimeout(() => {
      window.scrollTo(0, restore && next.name === returningTo ? listScroll.current : 0);
    }, 0);
  };

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => setHealth({ ready: false, error: "Cannot reach the Later API. Start the backend." }));
  }, []);

  useEffect(() => {
    if (!readyForRecs && view.name === "home") go({ name: "survey" });
  }, [readyForRecs, view.name]);

  useEffect(() => {
    if (view.name === "home" || listView.name === "home") setKeepHome(true);
    if (view.name === "browse" || listView.name === "browse") setKeepBrowse(true);
    if (view.name === "library" || listView.name === "library") setKeepLibrary(true);
  }, [view, listView]);

  const open = (id: number) => go({ name: "movie", id });
  const currentList = view.name === "movie" ? listView : listFrom(view);
  const browseGenre = currentList.name === "browse" ? currentList.genre : null;
  const navName = view.name === "movie" ? listView.name : view.name;

  return (
    <div className="shell">
      <header className="topbar">
        <button className="brand" onClick={() => go(readyForRecs ? { name: "home" } : { name: "survey" })}>
          <strong>Later</strong>
          <span>What to watch, and when</span>
        </button>
        <input
          className="search search-nav"
          placeholder="Search titles"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => {
            if (currentList.name === "survey") return;
            go({ name: "browse", genre: currentList.name === "browse" ? currentList.genre : null });
          }}
        />
        <nav className="nav">
          <button className={navName === "home" ? "active" : ""} onClick={() => go({ name: "home" })} disabled={!readyForRecs}>
            Home
          </button>
          <button className={navName === "browse" ? "active" : ""} onClick={() => go({ name: "browse", genre: null })}>
            Browse
          </button>
          <button className={navName === "library" ? "active" : ""} onClick={() => go({ name: "library" })}>
            Library
          </button>
          <button className={navName === "survey" ? "active" : ""} onClick={() => go({ name: "survey" })}>
            Survey
          </button>
        </nav>
      </header>

      {!health ? <p className="status">Loading…</p> : null}
      {health && !health.ready ? (
        <p className="status">{health.error || "Train the model first: python -m backend.train"}</p>
      ) : null}

      {health?.ready && keepHome ? (
        <div hidden={view.name !== "home"}>
          <Home onOpen={open} onSurvey={() => go({ name: "survey" })} />
        </div>
      ) : null}
      {health?.ready ? (
        <div hidden={view.name !== "survey"}>
          <Survey onOpen={open} onDone={() => go({ name: "home" })} />
        </div>
      ) : null}
      {health?.ready && keepBrowse ? (
        <div hidden={view.name !== "browse"}>
          <Browse
            genre={browseGenre}
            query={query}
            onOpen={open}
            onGenre={(genre) => go({ name: "browse", genre })}
          />
        </div>
      ) : null}
      {health?.ready && keepLibrary ? (
        <div hidden={view.name !== "library"}>
          <Library onOpen={open} />
        </div>
      ) : null}
      {health?.ready && view.name === "movie" ? (
        <MoviePage
          id={view.id}
          onOpen={open}
          onBack={() => go(listView)}
          backLabel={
            listView.name === "survey"
              ? "Back to survey"
              : listView.name === "browse"
                ? "Back to browse"
                : listView.name === "library"
                  ? "Back to library"
                  : "Back to home"
          }
        />
      ) : null}
    </div>
  );
}

function useRecs(language: string | null = null) {
  const { ratings, mood, readyForRecs, passed } = useRatings();
  const [data, setData] = useState<RecommendResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const hidden = useMemo(() => Object.keys(passed).map(Number), [passed]);
  const key = useMemo(
    () => JSON.stringify({ ratings, mood, language, hidden }),
    [ratings, mood, language, hidden]
  );

  useEffect(() => {
    let cancelled = false;
    setError(null);
    fetchRecommend({ ratings, mood, language, notInterested: hidden })
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [key, ratings, mood, language]);

  return { data, error, readyForRecs };
}

function LanguageFilter({
  value,
  options,
  onChange,
}: {
  value: string | null;
  options: { id: string; count: number }[];
  onChange: (language: string | null) => void;
}) {
  const [open, setOpen] = useState(false);
  if (!options.length) return null;
  const label = value ?? "All languages";
  return (
    <div className="lang-filter">
      <button type="button" className={`lang-toggle ${value ? "on" : ""}`} onClick={() => setOpen((prev) => !prev)}>
        Language · {label} {open ? "▴" : "▾"}
      </button>
      {open ? (
        <div className="lang-slider">
          <button className={!value ? "on" : ""} onClick={() => onChange(null)}>
            All languages
          </button>
          {options.map((item) => (
            <button key={item.id} className={value === item.id ? "on" : ""} onClick={() => onChange(item.id)}>
              {item.id}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function Home({ onOpen, onSurvey }: { onOpen: (id: number) => void; onSurvey: () => void }) {
  const { mood, setMood, readyForRecs, ratings, setRating, passed } = useRatings();
  const [foreignLang, setForeignLang] = useState<string | null>(null);
  const [languages, setLanguages] = useState<{ id: string; count: number }[]>([]);
  const { data, error } = useRecs(foreignLang);
  const top = withoutPassed(data?.top, passed);
  const indie = withoutPassed(data?.indie, passed);
  const niche = withoutPassed(data?.niche, passed);
  const foreign = withoutPassed(data?.foreign, passed);
  const tonight = withoutPassed(data?.tonight, passed);
  const weekend = withoutPassed(data?.weekend, passed);
  const weeknight = withoutPassed(data?.weeknight, passed);
  const hiddenGems = withoutPassed(data?.hidden, passed);
  const because = (data?.because ?? []).map((row) => ({ ...row, movies: withoutPassed(row.movies, passed) }));
  const genres = (data?.genres ?? []).map((row) => ({ ...row, movies: withoutPassed(row.movies, passed) }));
  const hero =
    data?.hero && !passed[data.hero.movie_id] ? data.hero : top[0] ?? tonight[0] ?? indie[0] ?? null;
  const vibe = mood !== "tonight";

  useEffect(() => {
    fetchForeignLanguages()
      .then(setLanguages)
      .catch(() => setLanguages([]));
  }, []);

  if (!readyForRecs) {
    return (
      <div className="banner" style={{ marginTop: 32 }}>
        <div>Finish the 8-film survey so Home can personalize like Netflix.</div>
        <button className="primary" onClick={onSurvey}>
          Start survey
        </button>
      </div>
    );
  }

  return (
    <div>
      <section className="energy">
        <p className="kicker">What mood are you in?</p>
        <div className="energy-row">
          {ENERGY.map((item) => (
            <button
              key={item.id}
              type="button"
              className={mood === item.id ? "on" : ""}
              onClick={() => setMood(mood === item.id ? "tonight" : item.id)}
            >
              <b>{item.title}</b>
              <span>{item.detail}</span>
            </button>
          ))}
        </div>
      </section>
      {error ? <p className="status">{error}</p> : null}
      {hero ? (
        <section className="hero">
          <button className="poster-hit" type="button" onClick={() => onOpen(hero.movie_id)}>
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
            <div className="hero-actions">
              <Stars value={ratings[hero.movie_id] ?? 0} onChange={(v) => setRating(hero.movie_id, v)} />
              <PassButton movieId={hero.movie_id} />
            </div>
            <div className="moods">
              {MOODS.map((item) => (
                <button key={item.id} className={mood === item.id ? "on" : ""} onClick={() => setMood(item.id)}>
                  {item.label}
                </button>
              ))}
            </div>
            {mood === "foreign" ? (
              <LanguageFilter value={foreignLang} options={languages} onChange={setForeignLang} />
            ) : null}
          </div>
        </section>
      ) : (
        <p className="status">Building your home row…</p>
      )}

      {mood === "tonight" && indie.length ? (
        <section className="section">
          <h2>Indie</h2>
          <MovieRow movies={indie} ratings={ratings} onOpen={onOpen} onRate={setRating} />
        </section>
      ) : null}
      {mood === "tonight" && niche.length ? (
        <section className="section">
          <h2>Niche</h2>
          <MovieRow movies={niche} ratings={ratings} onOpen={onOpen} onRate={setRating} />
        </section>
      ) : null}
      {mood === "tonight" && (foreign.length || languages.length) ? (
        <section className="section">
          <h2>Foreign</h2>
          <LanguageFilter value={foreignLang} options={languages} onChange={setForeignLang} />
          <MovieRow movies={foreign} ratings={ratings} onOpen={onOpen} onRate={setRating} />
        </section>
      ) : null}

      {!vibe && tonight.length ? (
        <section className="section">
          <h2>Right for this hour</h2>
          <MovieRow
            movies={tonight}
            ratings={ratings}
            onOpen={onOpen}
            onRate={setRating}
            subtitleFor={(m) => `${(m as RecMovie).watch.slot} · ${(m as RecMovie).watch.when}`}
          />
        </section>
      ) : null}
      {!vibe && weekend.length ? (
        <section className="section">
          <h2>Weekend watchlist</h2>
          <MovieRow movies={weekend} ratings={ratings} onOpen={onOpen} onRate={setRating} />
        </section>
      ) : null}
      {!vibe && weeknight.length ? (
        <section className="section">
          <h2>Weeknight unwind</h2>
          <MovieRow movies={weeknight} ratings={ratings} onOpen={onOpen} onRate={setRating} />
        </section>
      ) : null}
      {top.length ? (
        <section className="section">
          <h2>{vibe ? MOOD_ROW[mood] : "Top picks for you"}</h2>
          <MovieRow movies={top} ratings={ratings} onOpen={onOpen} onRate={setRating} />
        </section>
      ) : null}
      {because.map((row) =>
        row.movies.length ? (
          <section className="section" key={row.title}>
            <h2>Because you liked {row.title}</h2>
            <MovieRow movies={row.movies} ratings={ratings} onOpen={onOpen} onRate={setRating} />
          </section>
        ) : null
      )}
      {genres.map((row) =>
        row.movies.length ? (
          <section className="section" key={row.name}>
            <h2>{row.name}</h2>
            <MovieRow movies={row.movies} ratings={ratings} onOpen={onOpen} onRate={setRating} />
          </section>
        ) : null
      )}
      {hiddenGems.length ? (
        <section className="section">
          <h2>Hidden gems</h2>
          <MovieRow movies={hiddenGems} ratings={ratings} onOpen={onOpen} onRate={setRating} />
        </section>
      ) : null}
      <About />
    </div>
  );
}

function Survey({ onOpen, onDone }: { onOpen: (id: number) => void; onDone: () => void }) {
  const { ratings, setRating, count, clearRatings, readyForRecs } = useRatings();
  const [rows, setRows] = useState<{ name: string; movies: Movie[] }[]>([]);
  const [hits, setHits] = useState<Movie[] | null>(null);
  const [q, setQ] = useState("");
  const [genre, setGenre] = useState<string | null>(null);

  useEffect(() => {
    fetchSurvey().then(setRows).catch(() => setRows([]));
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

  const visibleRows = genre ? rows.filter((row) => row.name === genre) : rows;

  return (
    <div>
      <section className="hero" style={{ gridTemplateColumns: "1fr" }}>
        <div>
          <p className="kicker">Getting started</p>
          <h1>Rate films you actually know.</h1>
          <p className="lead">
            Each row is the most-rated, well-reviewed movies in that genre. Tap a half-star for 3½ or 4½ — you do
            not need to open the title. {count}/{MIN_RATINGS}
          </p>
          <div className="progress">
            <div className="progress-bar" style={{ width: `${Math.min(100, (count / MIN_RATINGS) * 100)}%` }} />
          </div>
          {readyForRecs ? (
            <button className="primary" style={{ marginTop: 16 }} onClick={onDone}>
              Go to Home
            </button>
          ) : null}
          <input
            className="search"
            style={{ marginTop: 18 }}
            placeholder="Search if a favorite is missing"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <div className="moods">
            <button className={!genre ? "on" : ""} onClick={() => setGenre(null)}>
              All genres
            </button>
            {rows.map((item) => (
              <button key={item.name} className={genre === item.name ? "on" : ""} onClick={() => setGenre(item.name)}>
                {item.name}
              </button>
            ))}
          </div>
          {count > 0 ? (
            <button className="ghost" onClick={clearRatings}>
              Clear my ratings
            </button>
          ) : null}
        </div>
      </section>
      {q.trim() ? (
        <div className="grid">
          {(hits ?? []).map((movie) => (
            <MovieCard
              key={movie.movie_id}
              movie={movie}
              rating={ratings[movie.movie_id]}
              onOpen={onOpen}
              onRate={setRating}
            />
          ))}
        </div>
      ) : (
        visibleRows.map((row) => (
          <section className="section" key={row.name}>
            <h2>Highest-rated {row.name}</h2>
            <MovieRow
              movies={row.movies}
              ratings={ratings}
              onOpen={onOpen}
              onRate={setRating}
              subtitleFor={(m) => `${m.avg_rating.toFixed(1)} avg · ${m.rating_count.toLocaleString()} ratings`}
            />
          </section>
        ))
      )}
    </div>
  );
}

function Browse({
  genre,
  query,
  onOpen,
  onGenre,
}: {
  genre: string | null;
  query: string;
  onOpen: (id: number) => void;
  onGenre: (genre: string | null) => void;
}) {
  const { ratings, setRating } = useRatings();
  const [genres, setGenres] = useState<{ id: string; count: number }[]>([]);
  const [movies, setMovies] = useState<Movie[]>([]);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    fetchGenres().then(setGenres).catch(() => setGenres([]));
  }, []);

  useEffect(() => {
    fetchBrowse(genre, query)
      .then((res) => {
        setMovies(res.movies);
        setTotal(res.total);
      })
      .catch(() => setMovies([]));
  }, [genre, query]);

  return (
    <div>
      <section className="hero" style={{ gridTemplateColumns: "1fr" }}>
        <div>
          <h1>{genre || (query ? `Results for “${query}”` : "Browse the catalog")}</h1>
          <p className="lead">{total.toLocaleString()} titles in this slice of MovieLens 32M.</p>
          <div className="moods">
            <button className={!genre ? "on" : ""} onClick={() => onGenre(null)}>
              All
            </button>
            {genres.map((item) => (
              <button key={item.id} className={genre === item.id ? "on" : ""} onClick={() => onGenre(item.id)}>
                {item.id}
              </button>
            ))}
          </div>
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

function Library({ onOpen }: { onOpen: (id: number) => void }) {
  const { ratings, setRating, passed } = useRatings();
  const [rated, setRated] = useState<Movie[]>([]);
  const [skipped, setSkipped] = useState<Movie[]>([]);
  const [ratedLoading, setRatedLoading] = useState(false);
  const ratedIds = useMemo(
    () => Object.keys(ratings).map(Number).sort((a, b) => (ratings[b] ?? 0) - (ratings[a] ?? 0)),
    [ratings]
  );
  const skippedIds = useMemo(() => Object.keys(passed).map(Number), [passed]);

  useEffect(() => {
    if (!ratedIds.length) {
      setRated([]);
      setRatedLoading(false);
      return;
    }
    setRatedLoading(true);
    fetchMovieBatch(ratedIds)
      .then(setRated)
      .catch(() => setRated([]))
      .finally(() => setRatedLoading(false));
  }, [ratedIds]);

  useEffect(() => {
    if (!skippedIds.length) {
      setSkipped([]);
      return;
    }
    fetchMovieBatch(skippedIds).then(setSkipped).catch(() => setSkipped([]));
  }, [skippedIds]);

  const ratedOrder = useMemo(() => {
    const byId = new Map(rated.map((movie) => [movie.movie_id, movie]));
    return ratedIds.map((id) => byId.get(id)).filter((movie): movie is Movie => Boolean(movie));
  }, [rated, ratedIds]);

  return (
    <div>
      <section className="hero" style={{ gridTemplateColumns: "1fr" }}>
        <div>
          <p className="kicker">Your films</p>
          <h1>Library</h1>
          <p className="lead">
            Everything you have rated lives here. Titles marked not interested stay out of Home and teach Later what
            to skip.
          </p>
        </div>
      </section>
      <section className="section">
        <h2>Rated ({ratedOrder.length})</h2>
        {ratedLoading && !ratedOrder.length ? (
          <p className="status">Loading your titles…</p>
        ) : ratedOrder.length ? (
          <div className="grid">
            {ratedOrder.map((movie) => (
              <MovieCard
                key={movie.movie_id}
                movie={movie}
                rating={ratings[movie.movie_id]}
                onOpen={onOpen}
                onRate={setRating}
                showPass={false}
              />
            ))}
          </div>
        ) : (
          <p className="status">Rate a film on Home, Browse, or the survey and it will show up here.</p>
        )}
      </section>
      <section className="section">
        <h2>Not interested ({skipped.length})</h2>
        {skipped.length ? (
          <div className="grid">
            {skipped.map((movie) => (
              <MovieCard
                key={movie.movie_id}
                movie={movie}
                rating={ratings[movie.movie_id]}
                onOpen={onOpen}
                onRate={setRating}
              />
            ))}
          </div>
        ) : (
          <p className="status">Tap ✕ on a poster or Not interested on a title to keep it off your recs.</p>
        )}
      </section>
    </div>
  );
}

function MoviePage({
  id,
  onOpen,
  onBack,
  backLabel,
}: {
  id: number;
  onOpen: (id: number) => void;
  onBack: () => void;
  backLabel: string;
}) {
  const { ratings, setRating, passed } = useRatings();
  const [movie, setMovie] = useState<Movie | null>(null);
  const { data } = useRecs();

  useEffect(() => {
    fetchMovie(id).then(setMovie).catch(() => setMovie(null));
  }, [id]);

  if (!movie) return <p className="status">Loading title…</p>;

  const similar = withoutPassed(data?.top, passed).filter((m) => m.movie_id !== id).slice(0, 12);
  const sameGenre = (data?.genres || []).find((row) => movie.genres.includes(row.name));
  const sameGenreMovies = withoutPassed(sameGenre?.movies, passed).filter((m) => m.movie_id !== id);

  return (
    <div>
      <button className="primary" style={{ marginTop: 20 }} onClick={onBack}>
        {backLabel}
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
          <p className="lead" style={{ marginBottom: 8 }}>
            Rate it here, then go back to the same list you were on.
          </p>
          <div className="hero-actions">
            <Stars value={ratings[movie.movie_id] ?? 0} onChange={(v) => setRating(movie.movie_id, v)} />
            <PassButton movieId={movie.movie_id} />
          </div>
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
          <MovieRow movies={similar} ratings={ratings} onOpen={onOpen} onRate={setRating} />
        </section>
      ) : null}
      {sameGenreMovies.length ? (
        <section className="section">
          <h2>More {sameGenre?.name}</h2>
          <MovieRow movies={sameGenreMovies} ratings={ratings} onOpen={onOpen} onRate={setRating} />
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
      Later is trained on MovieLens 32M with LensKit item–item CF (Harper & Konstan 2015; Ekstrand 2020). Catalog{" "}
      {String(metrics.catalog_movies)} movies, {String(metrics.training_users)} users, {String(metrics.training_ratings)}{" "}
      ratings. Holdout nDCG@20 {String(metrics.ndcg_at_20)}. This product uses the TMDB API but is not endorsed or
      certified by TMDB.
    </aside>
  );
}

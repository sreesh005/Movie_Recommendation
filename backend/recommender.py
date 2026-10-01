"""Hybrid LensKit + content + popularity recommender with watch-time windows."""

from __future__ import annotations

import json
import pickle
from dataclasses import dataclass

import numpy as np
import pandas as pd

from backend.config import (
    CATALOG_PATH,
    GENRE_PRIORITY,
    METRICS_PATH,
    MOOD_GENRES,
    MOODS,
    PIPELINE_PATH,
    POSTERS_PATH,
    STARTERS_PATH,
    WATCH_PATH,
    WATCH_RULES,
)

def _minmax(values: dict[int, float]) -> dict[int, float]:
    if not values:
        return {}
    nums = np.array(list(values.values()), dtype=float)
    lo, hi = float(nums.min()), float(nums.max())
    if hi - lo < 1e-9:
        return {k: 0.5 for k in values}
    return {k: (v - lo) / (hi - lo) for k, v in values.items()}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


@dataclass
class Movie:
    movie_id: int
    title: str
    year: int | None
    genres: list[str]
    tags: list[str]
    avg_rating: float
    rating_count: int
    bayes_avg: float
    imdb_id: str | None
    tmdb_id: int | None
    primary_genre: str
    poster_url: str | None = None

    def public(self, watch: dict) -> dict:
        return {
            "movie_id": self.movie_id,
            "title": self.title,
            "year": self.year,
            "genres": self.genres,
            "tags": self.tags,
            "avg_rating": round(self.avg_rating, 2),
            "rating_count": int(self.rating_count),
            "imdb_id": self.imdb_id,
            "tmdb_id": self.tmdb_id,
            "poster_url": self.poster_url,
            "watch": watch,
        }


class Engine:
    def __init__(self) -> None:
        self.ready = False
        self.error: str | None = None
        self.movies: dict[int, Movie] = {}
        self.watch_windows: dict[str, dict] = {}
        self.starters: list[int] = []
        self.metrics: dict = {}
        self.pipeline = None
        self.genre_index: dict[str, int] = {}
        self.genre_matrix: dict[int, np.ndarray] = {}
        self.pop_scores: dict[int, float] = {}
        self.search_docs: list[tuple[int, str]] = []
        self._posters_mtime: float | None = None

    def load(self) -> None:
        if not CATALOG_PATH.exists() or not PIPELINE_PATH.exists():
            self.error = "Model artifacts missing. Run: python -m backend.train"
            return
        catalog = pd.read_parquet(CATALOG_PATH)
        self.watch_windows = json.loads(WATCH_PATH.read_text(encoding="utf-8"))
        self.starters = json.loads(STARTERS_PATH.read_text(encoding="utf-8"))
        self.metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8")) if METRICS_PATH.exists() else {}

        for _, row in catalog.iterrows():
            mid = int(row["movieId"])
            genres = list(row["genres_list"]) if isinstance(row["genres_list"], (list, np.ndarray)) else []
            tags = list(row["tags"]) if isinstance(row["tags"], (list, np.ndarray)) else []
            year = row["year"]
            movie = Movie(
                movie_id=mid,
                title=str(row["display_title"]),
                year=None if pd.isna(year) else int(year),
                genres=[str(g) for g in genres],
                tags=[str(t) for t in tags],
                avg_rating=float(row["avg_rating"]),
                rating_count=int(row["rating_count"]),
                bayes_avg=float(row["bayes_avg"]),
                imdb_id=None if pd.isna(row["imdbId"]) else str(row["imdbId"]),
                tmdb_id=None if pd.isna(row["tmdbId"]) else int(row["tmdbId"]),
                primary_genre=str(row["primary_genre"]) if not pd.isna(row["primary_genre"]) else "Drama",
            )
            self.movies[mid] = movie
            self.pop_scores[mid] = float(row["bayes_avg"])
            blob = f"{movie.title} {movie.year or ''} {' '.join(movie.genres)}".lower()
            self.search_docs.append((mid, blob))

        all_genres = sorted({g for m in self.movies.values() for g in m.genres})
        self.genre_index = {g: i for i, g in enumerate(all_genres)}
        n = len(self.genre_index)
        for mid, movie in self.movies.items():
            vec = np.zeros(n, dtype=np.float32)
            for g in movie.genres:
                if g in self.genre_index:
                    vec[self.genre_index[g]] = 1.0
            norm = np.linalg.norm(vec)
            self.genre_matrix[mid] = vec / norm if norm else vec

        import lenskit.knn.item  # noqa: F401 — register class for pickle

        with PIPELINE_PATH.open("rb") as f:
            self.pipeline = pickle.load(f)
        self.refresh_posters()
        self.ready = True
        self.error = None

    def refresh_posters(self) -> None:
        if not POSTERS_PATH.exists():
            return
        mtime = POSTERS_PATH.stat().st_mtime
        if mtime == self._posters_mtime:
            return
        data = json.loads(POSTERS_PATH.read_text(encoding="utf-8"))
        self._posters_mtime = mtime
        for key, url in data.items():
            movie = self.movies.get(int(key))
            if movie and url:
                movie.poster_url = str(url)

    def watch_for(self, movie: Movie) -> dict:
        genre = movie.primary_genre if movie.primary_genre in self.watch_windows else primary_fallback(movie.genres)
        window = self.watch_windows.get(genre) or self.watch_windows.get("Drama")
        if not window:
            rule = WATCH_RULES.get(genre, WATCH_RULES["Comedy"])
            window = {**rule, "detail": f"A good time for {genre.lower()} is {rule['slot'].lower()}."}
        return {
            "genre": genre,
            "slot": window["slot"],
            "when": window["when"],
            "detail": window["detail"],
            "hours": window["hours"],
            "dows": window["dows"],
            "moods": window.get("moods", []),
        }

    def movie_public(self, movie_id: int) -> dict | None:
        self.refresh_posters()
        movie = self.movies.get(int(movie_id))
        if not movie:
            return None
        return movie.public(self.watch_for(movie))

    def search(self, query: str, limit: int = 24) -> list[dict]:
        q = query.strip().lower()
        if not q:
            return [self.movie_public(i) for i in self.starters[:limit] if i in self.movies]
        scored: list[tuple[int, int]] = []
        for mid, blob in self.search_docs:
            if q in blob:
                title = self.movies[mid].title.lower()
                rank = 0 if title.startswith(q) else (1 if q in title else 2)
                scored.append((rank, -self.movies[mid].rating_count, mid))
        scored.sort()
        return [self.movie_public(mid) for _, _, mid in scored[:limit]]

    def starter_movies(self) -> list[dict]:
        return [self.movie_public(i) for i in self.starters if i in self.movies]

    def _content_scores(self, ratings: dict[int, float]) -> dict[int, float]:
        if not ratings or not self.genre_index:
            return {}
        n = len(self.genre_index)
        profile = np.zeros(n, dtype=np.float32)
        for mid, rating in ratings.items():
            vec = self.genre_matrix.get(int(mid))
            if vec is None:
                continue
            profile += (float(rating) - 3.0) * vec
        norm = np.linalg.norm(profile)
        if norm:
            profile = profile / norm
        scores = {}
        for mid, vec in self.genre_matrix.items():
            if mid in ratings:
                continue
            scores[mid] = float(profile @ vec)
        return scores

    def _knn_scores(self, ratings: dict[int, float], n: int = 200) -> dict[int, float]:
        if not ratings or self.pipeline is None:
            return {}
        from lenskit.data import ItemList, RecQuery
        from lenskit.operations import recommend

        item_ids = [int(i) for i in ratings.keys() if int(i) in self.movies]
        if not item_ids:
            return {}
        history = ItemList(item_ids, rating=[float(ratings[i]) for i in item_ids])
        query = RecQuery(history_items=history)
        recs = recommend(self.pipeline, query, n=n)
        ids = recs.ids()
        scores = recs.scores()
        out = {}
        for item_id, score in zip(ids, scores):
            mid = int(item_id)
            if mid in ratings or mid not in self.movies:
                continue
            if score is None or (isinstance(score, float) and np.isnan(score)):
                continue
            out[mid] = float(score)
        return out

    def _because(self, rec_id: int, ratings: dict[int, float]) -> dict | None:
        rec = self.movies.get(rec_id)
        if not rec:
            return None
        rec_g = set(rec.genres)
        best_id = None
        best_score = 0.0
        for mid, rating in ratings.items():
            if rating < 3.5:
                continue
            other = self.movies.get(int(mid))
            if not other:
                continue
            score = _jaccard(rec_g, set(other.genres)) * (rating / 5.0)
            if other.primary_genre == rec.primary_genre:
                score += 0.15
            if score > best_score:
                best_score = score
                best_id = int(mid)
        if best_id is None or best_score < 0.12:
            liked = sorted(ratings.items(), key=lambda kv: kv[1], reverse=True)
            if liked:
                best_id = int(liked[0][0])
        movie = self.movies.get(best_id) if best_id else None
        if not movie:
            return None
        return {"movie_id": movie.movie_id, "title": movie.title}

    def _reason(self, movie: Movie, because: dict | None, knn: bool, mood: str | None) -> str:
        if because:
            return f"Because you liked {because['title']}"
        if mood == "tonight":
            return f"Fits {movie.primary_genre.lower()} tonight"
        if knn:
            return "People with your taste rated this highly"
        return f"Matches your {movie.primary_genre.lower()} streak"

    def recommend(
        self,
        ratings: dict[int, float],
        mood: str | None = None,
        hour: int | None = None,
        weekday: int | None = None,
        n: int = 40,
    ) -> dict:
        self.refresh_posters()
        ratings = {int(k): float(v) for k, v in ratings.items() if int(k) in self.movies}
        knn = self._knn_scores(ratings) if ratings else {}
        content = self._content_scores(ratings) if ratings else {}
        pop = {mid: score for mid, score in self.pop_scores.items() if mid not in ratings}

        n_r = len(ratings)
        if n_r == 0:
            w_knn, w_content, w_pop = 0.0, 0.0, 1.0
        elif n_r < 5:
            w_knn, w_content, w_pop = 0.35, 0.40, 0.25
        else:
            w_knn, w_content, w_pop = 0.62, 0.23, 0.15

        knn_n = _minmax(knn)
        content_n = _minmax(content)
        pop_n = _minmax(pop)

        candidates = set(knn) | set(list(sorted(content, key=content.get, reverse=True))[:120])
        candidates |= set(list(sorted(pop, key=pop.get, reverse=True))[:80])
        candidates -= set(ratings)
        candidates &= set(self.movies)

        mood_genres = MOOD_GENRES.get(mood) if mood else None
        ranked: list[tuple[float, int]] = []
        for mid in candidates:
            movie = self.movies[mid]
            watch = self.watch_for(movie)
            score = (
                w_knn * knn_n.get(mid, 0.0)
                + w_content * content_n.get(mid, 0.0)
                + w_pop * pop_n.get(mid, 0.0)
            )
            if mood_genres and set(movie.genres) & mood_genres:
                score += 0.18
            elif mood_genres:
                score -= 0.08
            tonight_fit = False
            if hour is not None and hour in watch["hours"]:
                score += 0.08
                tonight_fit = True
            if weekday is not None and weekday in watch["dows"]:
                score += 0.05
                tonight_fit = tonight_fit or (hour is not None and hour >= 18)
            if mood == "tonight" and tonight_fit:
                score += 0.12
            ranked.append((score, mid))

        ranked.sort(reverse=True)
        if mood_genres:
            preferred = [(s, mid) for s, mid in ranked if set(self.movies[mid].genres) & mood_genres]
            if len(preferred) >= min(12, n):
                ranked = preferred + [row for row in ranked if row not in preferred]

        rows = []
        used_because: set[int] = set()
        for score, mid in ranked[: max(n * 3, n)]:
            movie = self.movies[mid]
            because = self._because(mid, ratings) if ratings else None
            if because and because["movie_id"] in used_because and len(rows) < 8:
                # keep some variety in the lead explanations
                pass
            elif because:
                used_because.add(because["movie_id"])
            pred = knn.get(mid)
            if pred is None:
                pred = 2.5 + 2.0 * max(0.0, min(1.0, score))
            pred = float(np.clip(pred, 0.5, 5.0))
            watch = self.watch_for(movie)
            tonight_fit = hour is not None and hour in watch["hours"]
            public = movie.public(watch)
            public.update(
                {
                    "predicted_rating": round(pred, 2),
                    "reason": self._reason(movie, because, mid in knn, mood),
                    "because_you_liked": because,
                    "tonight_fit": bool(tonight_fit),
                    "hybrid_score": round(float(score), 4),
                }
            )
            rows.append(public)
            if len(rows) >= n:
                break

        hero = None
        if rows:
            fits = [r for r in rows if r.get("tonight_fit")]
            hero = (fits[0] if fits and mood in (None, "tonight") else rows[0])

        because_groups: dict[str, list[dict]] = {}
        for row in rows:
            key = (row.get("because_you_liked") or {}).get("title")
            if not key:
                continue
            because_groups.setdefault(key, []).append(row)

        hidden = sorted(
            [r for r in rows if r["rating_count"] < 15000],
            key=lambda r: r["predicted_rating"],
            reverse=True,
        )[:12]

        return {
            "hero": hero,
            "top": rows[:20],
            "tonight": [r for r in rows if r.get("tonight_fit")][:12] or rows[:12],
            "hidden": hidden,
            "because": [
                {"title": title, "movies": movies[:10]}
                for title, movies in list(because_groups.items())[:4]
            ],
            "count_ratings": n_r,
            "personalized": n_r >= 5,
        }


def primary_fallback(genres: list[str]) -> str:
    for candidate in GENRE_PRIORITY:
        if candidate in genres:
            return candidate
    return genres[0] if genres else "Drama"


_ENGINE: Engine | None = None


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None or not _ENGINE.ready:
        engine = Engine()
        engine.load()
        _ENGINE = engine
    return _ENGINE

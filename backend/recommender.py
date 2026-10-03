"""Hybrid recommender (ImplicitMF + genre + popularity) plus watch-time windows."""

from __future__ import annotations

import json
import pickle
from dataclasses import dataclass

import numpy as np
import pandas as pd

from backend.config import (
    ADULT_TAG_NEEDLES,
    CATALOG_PATH,
    DARK_TAG_NEEDLES,
    EASY_TAG_NEEDLES,
    FOCUS_TAG_NEEDLES,
    FOREIGN_MUST_IDS,
    FOREIGN_MUST_LANGS,
    FOREIGN_TAG_NEEDLES,
    FOREIGN_TAG_TOKENS,
    LANGUAGE_ORDER,
    NEEDLE_TO_LANGUAGE,
    TITLE_TO_LANGUAGE,
    TOKEN_TO_LANGUAGE,
    GENRE_ORDER,
    GENRE_PRIORITY,
    HEAVY_GENRES,
    INDIE_TAG_NEEDLES,
    MAINSTREAM_TAG_NEEDLES,
    METRICS_PATH,
    MOOD_GENRE_ROWS,
    MOOD_SEED_GENRES,
    NICHE_TAG_NEEDLES,
    IMF_PATH,
    PIPELINE_PATH,
    POSTERS_PATH,
    SCARY_TAG_NEEDLES,
    STARTERS_PATH,
    WARM_TAG_NEEDLES,
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


def _tag_hits(movie: Movie, needles: tuple[str, ...]) -> bool:
    tags = [str(tag).lower() for tag in movie.tags]
    return any(any(needle in tag for needle in needles) for tag in tags)


def fits_family(movie: Movie) -> bool:
    genres = set(movie.genres)
    if genres & {"Horror", "War", "Film-Noir"}:
        return False
    if _tag_hits(movie, ADULT_TAG_NEEDLES) or _tag_hits(movie, DARK_TAG_NEEDLES):
        return False
    if "Children" in genres and not (genres & {"Thriller", "Crime", "Horror"}):
        return True
    if movie.primary_genre == "Animation" and genres & {"Fantasy", "Adventure", "Children"}:
        return not bool(genres & {"Thriller", "Crime", "War", "Horror"})
    return False


def fits_scary(movie: Movie) -> bool:
    genres = set(movie.genres)
    if "Horror" in genres:
        return True
    return movie.primary_genre in {"Thriller", "Mystery"} and _tag_hits(movie, SCARY_TAG_NEEDLES)


def fits_date(movie: Movie) -> bool:
    genres = set(movie.genres)
    if "Romance" not in genres or "Horror" in genres:
        return False
    if _tag_hits(movie, DARK_TAG_NEEDLES) and "Comedy" not in genres:
        return False
    return True


def fits_comfort(movie: Movie) -> bool:
    genres = set(movie.genres)
    if genres & HEAVY_GENRES or "Romance" in genres:
        return False
    if _tag_hits(movie, DARK_TAG_NEEDLES):
        return False
    if movie.primary_genre == "Western" and "Drama" in genres:
        return False
    if "Comedy" in genres or movie.primary_genre in {"Comedy", "Musical", "Western"}:
        if "Drama" in genres and not (_tag_hits(movie, WARM_TAG_NEEDLES) or genres & {"Adventure", "Fantasy"}):
            return False
        return True
    return movie.primary_genre == "Documentary" and not (genres & HEAVY_GENRES)


def fits_thrills(movie: Movie) -> bool:
    genres = set(movie.genres)
    if genres & {"Children", "Horror"}:
        return False
    if movie.primary_genre == "Sci-Fi" and "Comedy" in genres and "Action" not in genres:
        return False
    if "Sci-Fi" in genres and "Crime" in genres and "Action" not in genres:
        return False
    if "War" in genres and "Action" not in genres:
        return False
    if movie.primary_genre in {"War", "Crime", "Drama"} and "Drama" in genres and "Comedy" not in genres:
        if "Sci-Fi" not in genres and "IMAX" not in genres:
            return False
    if movie.primary_genre in {"Action", "Adventure", "Sci-Fi"}:
        return True
    return "Action" in genres


def fits_focus(movie: Movie) -> bool:
    genres = set(movie.genres)
    if "Children" in genres:
        return False
    if _tag_hits(movie, FOCUS_TAG_NEEDLES) or _tag_hits(movie, DARK_TAG_NEEDLES):
        return "Comedy" not in genres or movie.primary_genre in {"Drama", "Thriller", "Crime", "Mystery"}
    if movie.primary_genre in {"War", "Film-Noir", "Documentary", "Mystery"}:
        return True
    if movie.primary_genre == "Drama" and "Comedy" not in genres:
        return True
    if movie.primary_genre in {"Crime", "Thriller"} and "Comedy" not in genres and "Action" not in genres:
        return True
    return False


def fits_easy(movie: Movie) -> bool:
    if fits_focus(movie):
        return False
    genres = set(movie.genres)
    if genres & {"War", "Film-Noir", "Horror", "Documentary"}:
        return False
    if genres & {"Crime", "Thriller"} and "Drama" in genres:
        return False
    if _tag_hits(movie, DARK_TAG_NEEDLES) or _tag_hits(movie, FOCUS_TAG_NEEDLES):
        return False
    if _tag_hits(movie, EASY_TAG_NEEDLES) or _tag_hits(movie, WARM_TAG_NEEDLES):
        return True
    if movie.primary_genre in {"Comedy", "Musical", "Children", "Animation"}:
        return True
    if movie.primary_genre in {"Action", "Adventure", "Fantasy"} and "Drama" not in genres:
        return True
    if "Comedy" in genres and not (genres & {"Horror", "Crime", "Thriller"}):
        return True
    return False


def assigned_vibe(movie: Movie) -> str | None:
    if fits_family(movie):
        return "family"
    if fits_scary(movie):
        return "scary"
    if fits_date(movie):
        return "date"
    if "Action" in movie.genres and fits_thrills(movie):
        return "thrills"
    if movie.primary_genre in {"Adventure", "Sci-Fi"} and fits_thrills(movie):
        return "thrills"
    if fits_comfort(movie):
        return "comfort"
    if fits_thrills(movie):
        return "thrills"
    return None


def looks_foreign(movie: Movie) -> bool:
    if movie.movie_id in FOREIGN_MUST_IDS:
        return True
    tokens = {str(tag).lower() for tag in movie.tags}
    if tokens & FOREIGN_TAG_TOKENS:
        return True
    if _tag_hits(movie, FOREIGN_TAG_NEEDLES):
        return True
    title = movie.title or ""
    if any(ord(ch) > 127 for ch in title):
        return True
    lowered = title.lower()
    return any(
        marker in lowered
        for marker in (
            "kamikakushi",
            "shichinin",
            "mononoke",
            "hauru",
            "cidade",
            "laberinto",
            "vita è",
            "vita e bella",
            "amélie",
            "amelie",
            "intouchables",
            "das leben",
            "le fabuleux",
            "sen to chihiro",
        )
    )


def infer_language(movie: Movie) -> str | None:
    known = FOREIGN_MUST_LANGS.get(movie.movie_id)
    if known:
        return known
    tokens = {str(tag).lower() for tag in movie.tags}
    for token, language in TOKEN_TO_LANGUAGE.items():
        if token in tokens:
            return language
    tags = [str(tag).lower() for tag in movie.tags]
    for needle, language in NEEDLE_TO_LANGUAGE.items():
        if any(needle in tag for tag in tags):
            return language
    title = (movie.title or "").lower()
    for marker, language in TITLE_TO_LANGUAGE.items():
        if marker in title:
            return language
    if looks_foreign(movie):
        return "Other"
    return None


DISCOVERY_MOODS = ("foreign", "indie", "niche")
ENERGY_MOODS = ("easy", "focus")


def _discovery_ok(movie: Movie) -> bool:
    if movie.rating_count >= 50000:
        return False
    if _tag_hits(movie, MAINSTREAM_TAG_NEEDLES):
        return False
    if "Children" in movie.genres and movie.rating_count >= 18000:
        return False
    return True


def discovery_lane(movie: Movie) -> str | None:
    """Assign a title to at most one of foreign, indie, or niche."""
    if not _discovery_ok(movie):
        return None
    foreign = looks_foreign(movie) and movie.avg_rating >= 3.4
    indie = _tag_hits(movie, INDIE_TAG_NEEDLES) and movie.avg_rating >= 3.4
    niche = _tag_hits(movie, NICHE_TAG_NEEDLES) and movie.avg_rating >= 3.4
    modest = movie.rating_count <= 12000 and movie.avg_rating >= 3.75
    if modest and movie.primary_genre in {"Documentary", "Film-Noir", "Drama", "Mystery"}:
        niche = True
    if movie.rating_count <= 4000 and movie.avg_rating >= 3.9 and movie.rating_count >= 250:
        niche = True
    if movie.rating_count >= 28000:
        if not foreign:
            niche = False
        if not foreign and not indie:
            return None
    if foreign:
        return "foreign"
    if indie:
        return "indie"
    if niche:
        return "niche"
    return None


def fits_mood(movie: Movie, mood: str | None) -> bool:
    if not mood or mood == "tonight":
        return True
    if mood in DISCOVERY_MOODS:
        return discovery_lane(movie) == mood
    if mood in ENERGY_MOODS:
        return fits_easy(movie) if mood == "easy" else fits_focus(movie)
    return assigned_vibe(movie) == mood


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
            "language": infer_language(self),
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
        self.imf = None
        self.genre_index: dict[str, int] = {}
        self.genre_matrix: dict[int, np.ndarray] = {}
        self.pop_scores: dict[int, float] = {}
        self.search_docs: list[tuple[int, str]] = []
        self._posters_mtime: float | None = None
        self.genre_movies: dict[str, list[int]] = {}
        self.genre_list: list[dict] = []
        self.lane_ids: dict[str, list[int]] = {"indie": [], "niche": [], "foreign": []}

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
            self.pop_scores[mid] = float(np.log1p(max(0, int(row["rating_count"]))))
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
            self.genre_matrix[mid] = vec / norm if vec.any() else vec

        buckets: dict[str, list[int]] = {g: [] for g in GENRE_ORDER}
        for mid, movie in self.movies.items():
            for genre in movie.genres:
                buckets.setdefault(genre, []).append(mid)
        for genre, ids in buckets.items():
            ids.sort(key=lambda movie_id: self.movies[movie_id].bayes_avg, reverse=True)
            self.genre_movies[genre] = ids
        self.genre_list = [
            {"id": genre, "count": len(self.genre_movies.get(genre, []))}
            for genre in GENRE_ORDER
            if self.genre_movies.get(genre)
        ]
        buckets = {"indie": [], "niche": [], "foreign": []}
        for mid, movie in self.movies.items():
            lane = discovery_lane(movie)
            if lane:
                buckets[lane].append(mid)
        for lane, ids in buckets.items():
            ids.sort(key=lambda movie_id: (-self.movies[movie_id].bayes_avg, self.movies[movie_id].rating_count))
            self.lane_ids[lane] = ids

        import lenskit.knn.item  # noqa: F401  needed to unpickle
        import lenskit.als  # noqa: F401  needed to unpickle

        with PIPELINE_PATH.open("rb") as f:
            self.pipeline = pickle.load(f)
        self.imf = None
        if IMF_PATH.exists():
            with IMF_PATH.open("rb") as f:
                self.imf = pickle.load(f)
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

    def survey_rows(self, per_genre: int = 16) -> list[dict]:
        """Well-known, highly rated movies for the survey, one row per genre."""
        self.refresh_posters()
        rows = []
        for genre in GENRE_ORDER:
            ranked = [
                mid
                for mid in self.genre_movies.get(genre, [])
                if self.movies[mid].primary_genre == genre
            ]
            known = [
                mid
                for mid in ranked
                if self.movies[mid].rating_count >= 2500 and self.movies[mid].avg_rating >= 3.55
            ]
            known.sort(key=lambda mid: (-self.movies[mid].rating_count, -self.movies[mid].avg_rating))
            fallback = sorted(ranked, key=lambda mid: (-self.movies[mid].rating_count, -self.movies[mid].avg_rating))
            chosen = known[:per_genre] if len(known) >= 8 else fallback[:per_genre]
            movies = [m for m in (self.movie_public(mid) for mid in chosen) if m]
            if movies:
                rows.append({"name": genre, "movies": movies})
        return rows

    def genres(self) -> list[dict]:
        self.refresh_posters()
        return self.genre_list

    def foreign_languages(self) -> list[dict]:
        counts: dict[str, int] = {}
        for mid in self.lane_ids.get("foreign", []):
            language = infer_language(self.movies[mid])
            if not language:
                continue
            counts[language] = counts.get(language, 0) + 1
        ordered = [name for name in LANGUAGE_ORDER if name in counts]
        ordered += [name for name in sorted(counts) if name not in LANGUAGE_ORDER]
        return [{"id": name, "count": counts[name]} for name in ordered]

    def browse(self, genre: str | None = None, q: str = "", limit: int = 48) -> dict:
        self.refresh_posters()
        query = q.strip().lower()
        if genre:
            ids = list(self.genre_movies.get(genre, []))
        else:
            ids = sorted(self.movies.keys(), key=lambda mid: self.movies[mid].bayes_avg, reverse=True)
        if query:
            ids = [mid for mid in ids if query in self.movies[mid].title.lower()]
        movies = [self.movie_public(mid) for mid in ids[:limit]]
        return {"genre": genre, "total": len(ids), "movies": movies}

    def movies_public(self, ids: list[int]) -> list[dict]:
        self.refresh_posters()
        out = []
        seen: set[int] = set()
        for raw in ids[:240]:
            mid = int(raw)
            if mid in seen:
                continue
            seen.add(mid)
            payload = self.movie_public(mid)
            if payload:
                out.append(payload)
        return out

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
        pipe = self.imf if self.imf is not None else self.pipeline
        if not ratings or pipe is None:
            return {}
        from lenskit.data import ItemList, RecQuery
        from lenskit.operations import recommend

        source = ratings
        if self.imf is not None:
            liked = {mid: score for mid, score in ratings.items() if score >= 4.0}
            source = liked or ratings
        item_ids = [int(i) for i in source.keys() if int(i) in self.movies]
        if not item_ids:
            return {}
        history = ItemList(item_ids, rating=[float(source[i]) for i in item_ids])
        query = RecQuery(history_items=history)
        recs = recommend(pipe, query, n=n)
        ids = recs.ids()
        scores = recs.scores()
        out = {}
        for item_id, score in zip(ids, scores):
            mid = int(item_id)
            if mid in ratings or mid not in self.movies:
                continue
            if score is None or (isinstance(score, float) and np.isnan(score)):
                continue
            movie = self.movies[mid]
            out[mid] = float(score) * np.log1p(max(0, movie.rating_count))
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
        if mood == "date":
            return "Romance-first — not a prestige gut-punch"
        if mood == "family":
            return "Actually watchable with kids in the room"
        if mood == "scary":
            return "Horror, not just a tense drama"
        if mood == "comfort":
            return "Easy company — no dark comedies, no misery"
        if mood == "thrills":
            return "Built for pulse, not a quiet night in"
        if mood == "easy":
            return "Laid-back — you can half-watch this"
        if mood == "focus":
            return "This one asks you to actually pay attention"
        if mood == "indie":
            return "Independent — small-scale, not a studio machine"
        if mood == "niche":
            return "Cult, arthouse, or happily off the main road"
        if mood == "foreign":
            return "Made outside the usual Hollywood pipeline"
        if because:
            return f"Because you liked {because['title']}"
        if mood == "tonight":
            return f"Fits {movie.primary_genre.lower()} tonight"
        if knn:
            return "People with your taste rated this highly"
        return f"Matches your {movie.primary_genre.lower()} streak"

    def _mood_pool(
        self,
        mood: str | None,
        ratings: dict[int, float],
        base: set[int],
        language: str | None = None,
        blocked: set[int] | None = None,
    ) -> set[int]:
        skip = blocked if blocked is not None else set(ratings)
        if not mood or mood == "tonight":
            return base
        if mood in self.lane_ids:
            eligible = [mid for mid in self.lane_ids[mood] if mid not in skip]
            if mood == "foreign" and language:
                eligible = [mid for mid in eligible if infer_language(self.movies[mid]) == language]
            preferred = [mid for mid in eligible if mid in base]
            extra = [mid for mid in eligible if mid not in base]
            return set((preferred + extra)[:140])
        pool = {mid for mid in base if mid in self.movies and fits_mood(self.movies[mid], mood)}
        for genre in MOOD_SEED_GENRES.get(mood, []):
            for mid in self.genre_movies.get(genre, []):
                if mid in skip or mid not in self.movies:
                    continue
                if fits_mood(self.movies[mid], mood):
                    pool.add(mid)
                if len(pool) >= 90:
                    return pool
        return pool

    def _rec_payload(
        self,
        mid: int,
        score: float,
        knn: dict[int, float],
        ratings: dict[int, float],
        mood: str | None,
        hour: int | None,
        used_because: set[int],
    ) -> dict:
        movie = self.movies[mid]
        because = self._because(mid, ratings) if ratings else None
        if because and because["movie_id"] not in used_because:
            used_because.add(because["movie_id"])
        pred = float(np.clip(movie.bayes_avg, 0.5, 5.0))
        watch = self.watch_for(movie)
        public = movie.public(watch)
        public.update(
            {
                "predicted_rating": round(pred, 2),
                "reason": self._reason(movie, because, mid in knn, mood),
                "because_you_liked": because,
                "tonight_fit": bool(hour is not None and hour in watch["hours"]),
                "hybrid_score": round(float(score), 4),
            }
        )
        return public

    def _score_lane(
        self,
        lane: str,
        ratings: dict[int, float],
        knn: dict[int, float],
        knn_n: dict[int, float],
        content_n: dict[int, float],
        pop_n: dict[int, float],
        w_knn: float,
        w_content: float,
        w_pop: float,
        personal: set[int],
        hour: int | None,
        language: str | None = None,
        blocked: set[int] | None = None,
    ) -> list[dict]:
        ids = self.lane_ids.get(lane, [])
        skip = blocked or set()
        if lane == "foreign" and language:
            ids = [mid for mid in ids if infer_language(self.movies[mid]) == language]
        scored: list[tuple[float, int]] = []
        seen: set[int] = set()
        used: set[int] = set()
        for mid in list(personal & set(ids)) + ids:
            if mid in ratings or mid in skip or mid in seen:
                continue
            seen.add(mid)
            score = (
                w_knn * knn_n.get(mid, 0.0)
                + w_content * content_n.get(mid, 0.0)
                + w_pop * pop_n.get(mid, 0.0)
            )
            if lane == "foreign" and looks_foreign(self.movies[mid]):
                score += 0.07
            scored.append((score, mid))
            if len(scored) >= 220:
                break
        scored.sort(reverse=True)
        return [
            self._rec_payload(mid, score, knn, ratings, lane, hour, used)
            for score, mid in scored[:16]
        ]

    def recommend(
        self,
        ratings: dict[int, float],
        mood: str | None = None,
        hour: int | None = None,
        weekday: int | None = None,
        n: int = 40,
        language: str | None = None,
        not_interested: list[int] | None = None,
    ) -> dict:
        self.refresh_posters()
        ratings = {int(k): float(v) for k, v in ratings.items() if int(k) in self.movies}
        skipped = {int(i) for i in (not_interested or []) if int(i) in self.movies}
        blocked = set(ratings) | skipped
        knn = self._knn_scores(ratings) if ratings else {}
        content = self._content_scores(ratings) if ratings else {}
        pop = {mid: score for mid, score in self.pop_scores.items() if mid not in blocked}

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

        reject = np.zeros(len(self.genre_index) or 1, dtype=np.float32)
        if skipped and self.genre_index:
            reject = np.zeros(len(self.genre_index), dtype=np.float32)
            for mid in skipped:
                vec = self.genre_matrix.get(mid)
                if vec is not None:
                    reject += vec
            norm = np.linalg.norm(reject)
            if norm:
                reject = reject / norm

        candidates = set(knn) | set(list(sorted(content, key=content.get, reverse=True))[:120])
        candidates |= set(list(sorted(pop, key=pop.get, reverse=True))[:200])
        candidates -= blocked
        candidates &= set(self.movies)
        candidates = self._mood_pool(mood, ratings, candidates, language=language, blocked=blocked)

        if mood == "tonight" and hour is not None:
            timed = {mid for mid in candidates if hour in self.watch_for(self.movies[mid])["hours"]}
            if len(timed) >= 24:
                candidates = timed

        ranked: list[tuple[float, int]] = []
        for mid in candidates:
            movie = self.movies[mid]
            watch = self.watch_for(movie)
            score = (
                w_knn * knn_n.get(mid, 0.0)
                + w_content * content_n.get(mid, 0.0)
                + w_pop * pop_n.get(mid, 0.0)
            )
            if skipped:
                vec = self.genre_matrix.get(mid)
                if vec is not None:
                    score -= 0.22 * float(vec @ reject)
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
            pred = float(np.clip(movie.bayes_avg, 0.5, 5.0))
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
            if mood in (None, "tonight"):
                fits = [r for r in rows if r.get("tonight_fit")]
                hero = fits[0] if fits else rows[0]
            else:
                hero = rows[0]

        because_groups: dict[str, list[dict]] = {}
        for row in rows:
            key = (row.get("because_you_liked") or {}).get("title")
            if not key:
                continue
            because_groups.setdefault(key, []).append(row)

        hidden = sorted(
            [r for r in rows if r["rating_count"] < 8000],
            key=lambda r: r["predicted_rating"],
            reverse=True,
        )[:16]

        weekend = [
            r
            for r in rows
            if set(r["watch"]["dows"]) & {5, 6} or r["watch"]["slot"].lower().find("weekend") >= 0
        ][:16]
        if len(weekend) < 8:
            weekend = rows[:16]

        weeknight = [
            r
            for r in rows
            if set(r["watch"]["dows"]) & {0, 1, 2, 3} or "weeknight" in r["watch"]["slot"].lower()
        ][:16]
        if len(weeknight) < 8:
            weeknight = rows[4:20]

        genre_order = MOOD_GENRE_ROWS.get(mood or "", GENRE_ORDER)
        genre_rows = []
        score_by_id = {r["movie_id"]: r for r in rows}
        vibe = mood not in (None, "tonight")
        for genre in genre_order:
            picked = [r for r in rows if genre in r["genres"]][:16]
            if len(picked) < 8:
                for mid in self.genre_movies.get(genre, []):
                    if mid in blocked or any(p["movie_id"] == mid for p in picked):
                        continue
                    if vibe and not fits_mood(self.movies[mid], mood):
                        continue
                    if mid in score_by_id:
                        picked.append(score_by_id[mid])
                    else:
                        public = self.movie_public(mid)
                        if public:
                            public.update(
                                {
                                    "predicted_rating": round(float(self.movies[mid].avg_rating), 2),
                                    "reason": f"Popular in {genre.lower()}",
                                    "because_you_liked": None,
                                    "tonight_fit": False,
                                    "hybrid_score": 0.0,
                                }
                            )
                            picked.append(public)
                    if len(picked) >= 16:
                        break
            if picked:
                genre_rows.append({"name": genre, "movies": picked[:16]})
            if len(genre_rows) >= (4 if vibe else 10):
                break

        personal = set(knn) | set(content)
        lane_rows = {}
        for lane in ("indie", "niche", "foreign"):
            if mood == lane:
                lane_rows[lane] = rows[:16]
            else:
                lane_rows[lane] = self._score_lane(
                    lane,
                    ratings,
                    knn,
                    knn_n,
                    content_n,
                    pop_n,
                    w_knn,
                    w_content,
                    w_pop,
                    personal,
                    hour,
                    language=language,
                    blocked=blocked,
                )

        return {
            "hero": hero,
            "top": rows[:20],
            "tonight": [r for r in rows if r.get("tonight_fit")][:16] or rows[:16],
            "weekend": weekend if not vibe else [],
            "weeknight": weeknight if not vibe else [],
            "hidden": hidden if not vibe else [],
            "because": [
                {"title": title, "movies": movies[:12]}
                for title, movies in list(because_groups.items())[:4]
            ],
            "genres": genre_rows,
            "mood": mood or "tonight",
            "indie": lane_rows["indie"],
            "niche": lane_rows["niche"],
            "foreign": lane_rows["foreign"],
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

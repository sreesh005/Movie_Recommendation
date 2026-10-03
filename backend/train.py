"""Trains ItemKNN on MovieLens 32M (movies with 20+ ratings), then runs the eval."""

from __future__ import annotations

import argparse
import json
import pickle
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from backend.config import (
    ARTIFACTS,
    CATALOG_PATH,
    GENRE_PRIORITY,
    KNN_NEIGHBORS,
    LINKS_CSV,
    METRICS_PATH,
    MIN_MOVIE_RATINGS,
    MIN_USER_RATINGS,
    MOVIES_CSV,
    PIPELINE_PATH,
    RATING_TIMEZONE,
    RATINGS_CSV,
    SAVE_NBRS,
    STARTER_MUST_IDS,
    STARTERS_PATH,
    TAGS_CSV,
    TRAIN_INFO_PATH,
    WATCH_PATH,
    WATCH_RULES,
    RANDOM_SEED,
)

TITLE_YEAR_RE = re.compile(r"\s*\((\d{4})\)\s*$")
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def log(msg: str) -> None:
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"), flush=True)


def parse_year(title: str) -> int | None:
    match = TITLE_YEAR_RE.search(title)
    return int(match.group(1)) if match else None


def display_title(title: str) -> str:
    return TITLE_YEAR_RE.sub("", title).strip()


def parse_genres(raw: str) -> list[str]:
    if not raw or raw == "(no genres listed)":
        return []
    return [g for g in str(raw).split("|") if g]


def primary_genre(genres: list[str]) -> str:
    for candidate in GENRE_PRIORITY:
        if candidate in genres:
            return candidate
    return genres[0] if genres else "Drama"


def hour_label(hour: int) -> str:
    display = hour % 12 or 12
    suffix = "am" if hour % 24 < 12 else "pm"
    return f"{display}{suffix}"


def build_watch_windows(genre_hour: dict[str, np.ndarray], genre_dow: dict[str, np.ndarray]) -> dict:
    windows = {}
    for genre, rule in WATCH_RULES.items():
        hours = genre_hour.get(genre)
        dows = genre_dow.get(genre)
        peak_hour = int(hours.argmax()) if hours is not None and hours.sum() else rule["hours"][0]
        peak_dow = int(dows.argmax()) if dows is not None and dows.sum() else rule["dows"][0]
        n_obs = int(hours.sum()) if hours is not None else 0
        windows[genre] = {
            "slot": rule["slot"],
            "when": rule["when"],
            "hours": rule["hours"],
            "dows": rule["dows"],
            "moods": rule["moods"],
            "peak_hour": peak_hour,
            "peak_dow": peak_dow,
            "n_obs": n_obs,
            "detail": (
                f"Best as a {rule['slot'].lower()} watch ({rule['when'].lower()}). "
                f"MovieLens users logged the most {genre.lower()} ratings on "
                f"{WEEKDAYS[peak_dow]}s around {hour_label(peak_hour)} "
                f"(timestamps in {RATING_TIMEZONE}; rating time is a proxy, not a viewing diary)."
            ),
        }
    windows["Drama"] = windows.get("Drama") or {
        "slot": "Sunday evening",
        "when": "When you can pay attention",
        "hours": list(range(19, 22)),
        "dows": [6],
        "moods": ["date"],
        "peak_hour": 20,
        "peak_dow": 6,
        "n_obs": 0,
        "detail": "A drama is best when you can sit with it — Sunday evening works well.",
    }
    return windows


def count_movie_ratings(path: Path) -> Counter:
    counts: Counter = Counter()
    log("Counting ratings per movie (32M rows)...")
    t0 = time.time()
    for i, chunk in enumerate(pd.read_csv(path, usecols=["movieId"], chunksize=1_500_000), start=1):
        counts.update(chunk["movieId"].value_counts().to_dict())
        if i % 5 == 0:
            log(f"  scanned {i * 1_500_000:,} rows...")
    log(f"  done in {time.time() - t0:.1f}s — {len(counts):,} movies have ratings")
    return counts


def stream_catalog_ratings(
    ratings_path: Path,
    keep_ids: set[int],
    movie_genres: dict[int, list[str]],
    parquet_path: Path,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], int]:
    log("Streaming catalog ratings, watch-time histograms, and parquet...")
    genre_hour = defaultdict(lambda: np.zeros(24, dtype=np.int64))
    genre_dow = defaultdict(lambda: np.zeros(7, dtype=np.int64))
    writer = None
    n_kept = 0
    t0 = time.time()
    keep_index = pd.Index(keep_ids)

    for i, chunk in enumerate(
        pd.read_csv(ratings_path, chunksize=1_200_000),
        start=1,
    ):
        sub = chunk[chunk["movieId"].isin(keep_index)]
        if sub.empty:
            continue
        ts = pd.to_datetime(sub["timestamp"], unit="s", utc=True).dt.tz_convert(RATING_TIMEZONE)
        tmp = pd.DataFrame(
            {
                "movieId": sub["movieId"].to_numpy(),
                "hour": ts.dt.hour.to_numpy(),
                "dow": ts.dt.dayofweek.to_numpy(),
                "genre": sub["movieId"].map(movie_genres),
            }
        )
        tmp = tmp.explode("genre").dropna(subset=["genre"])
        gh = tmp.groupby(["genre", "hour"]).size()
        gd = tmp.groupby(["genre", "dow"]).size()
        for (genre, hour), n in gh.items():
            genre_hour[str(genre)][int(hour)] += int(n)
        for (genre, dow), n in gd.items():
            genre_dow[str(genre)][int(dow)] += int(n)

        table = pa.Table.from_pandas(sub, preserve_index=False)
        if writer is None:
            writer = pq.ParquetWriter(parquet_path, table.schema)
        writer.write_table(table)
        n_kept += len(sub)
        if i % 4 == 0:
            log(f"  kept {n_kept:,} catalog ratings so far...")

    if writer is not None:
        writer.close()
    log(f"  wrote {n_kept:,} ratings in {time.time() - t0:.1f}s")
    return dict(genre_hour), dict(genre_dow), n_kept


def pick_starters(catalog: pd.DataFrame) -> list[int]:
    by_count = catalog.sort_values("rating_count", ascending=False)
    picked: list[int] = []
    seen: set[int] = set()
    for mid in STARTER_MUST_IDS:
        if mid in catalog.index and mid not in seen:
            picked.append(int(mid))
            seen.add(mid)
    genre_quota: dict[str, int] = defaultdict(int)
    for mid, row in by_count.iterrows():
        mid = int(mid)
        if mid in seen:
            continue
        genres = list(row["genres"])
        if any(genre_quota[g] < 5 for g in genres[:2]) or len(picked) < 24:
            picked.append(mid)
            seen.add(mid)
            for g in genres[:2]:
                genre_quota[g] += 1
        if len(picked) >= 80:
            break
    return picked


def evaluate_itemknn(pipe, fit: pd.DataFrame, hold: pd.DataFrame) -> dict:
    from lenskit.data import ItemList, RecQuery
    from lenskit.operations import recommend

    log(f"Evaluating ItemKNN on {hold.userId.nunique()} held-out users...")
    history = fit.groupby("userId")
    hits = 0
    total = 0
    ndcg_sum = 0.0
    n_scored = 0
    for uid, truth_df in hold.groupby("userId"):
        try:
            hist = history.get_group(uid)
        except KeyError:
            continue
        truth = set(int(x) for x in truth_df["movieId"])
        query = RecQuery(
            history_items=ItemList(
                [int(x) for x in hist["movieId"]],
                rating=[float(x) for x in hist["rating"]],
            )
        )
        recs = recommend(pipe, query, n=20)
        rec_ids = [int(x) for x in recs.ids()]
        rec_set = set(rec_ids)
        hits += len(rec_set & truth)
        total += len(truth)
        dcg = 0.0
        for rank, item in enumerate(rec_ids, start=1):
            if item in truth:
                dcg += 1.0 / np.log2(rank + 1)
        ideal = sum(1.0 / np.log2(i + 1) for i in range(1, min(len(truth), 20) + 1))
        ndcg_sum += dcg / ideal if ideal else 0.0
        n_scored += 1

    metrics = {
        "users_evaluated": n_scored,
        "recall_at_20": round(hits / total, 4) if total else 0.0,
        "ndcg_at_20": round(ndcg_sum / n_scored, 4) if n_scored else 0.0,
        "holdout_items_per_user": 5,
        "algorithm": "LensKit ItemKNNScorer (item-item CF)",
    }
    log(f"  recall@20={metrics['recall_at_20']}  nDCG@20={metrics['ndcg_at_20']}")
    return metrics


def train(quick: bool = False) -> None:
    n_movies_cap = 1500 if quick else None
    n_users_cap = 4000 if quick else None
    ARTIFACTS.mkdir(exist_ok=True)

    log("Loading movies and links...")
    movies = pd.read_csv(MOVIES_CSV)
    links = pd.read_csv(LINKS_CSV)
    movies["year"] = movies["title"].map(parse_year)
    movies["display_title"] = movies["title"].map(display_title)
    movies["genres_list"] = movies["genres"].map(parse_genres)
    movies["primary_genre"] = movies["genres_list"].map(primary_genre)
    movie_genres = dict(zip(movies["movieId"].astype(int), movies["genres_list"]))

    counts = count_movie_ratings(RATINGS_CSV)
    if n_movies_cap:
        keep = {int(m) for m, _ in counts.most_common(n_movies_cap)}
        log(f"Quick mode: keeping top {len(keep):,} movies")
    else:
        keep = {int(m) for m, c in counts.items() if c >= MIN_MOVIE_RATINGS}
        log(f"Full catalog: keeping {len(keep):,} movies with >= {MIN_MOVIE_RATINGS} ratings")

    raw_parquet = ARTIFACTS / "catalog_ratings.parquet"
    reuse = False
    if raw_parquet.exists() and TRAIN_INFO_PATH.exists() and WATCH_PATH.exists():
        try:
            info = json.loads(TRAIN_INFO_PATH.read_text(encoding="utf-8"))
            reuse = (
                not quick
                and info.get("full") is True
                and int(info.get("catalog_movies", -1)) == len(keep)
                and int(pq.ParquetFile(raw_parquet).metadata.num_rows) > 30_000_000
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            reuse = False
    if reuse:
        log("Reusing existing catalog ratings parquet and watch windows")
        watch_windows = json.loads(WATCH_PATH.read_text(encoding="utf-8"))
        n_catalog_ratings = int(pq.ParquetFile(raw_parquet).metadata.num_rows)
    else:
        if raw_parquet.exists():
            raw_parquet.unlink()
        genre_hour, genre_dow, n_catalog_ratings = stream_catalog_ratings(
            RATINGS_CSV, keep, movie_genres, raw_parquet
        )
        watch_windows = build_watch_windows(genre_hour, genre_dow)
        WATCH_PATH.write_text(json.dumps(watch_windows, indent=2), encoding="utf-8")

    log("Loading catalog ratings parquet...")
    catalog_ratings = pd.read_parquet(raw_parquet)
    user_counts = catalog_ratings.groupby("userId").size()
    eligible = user_counts[user_counts >= MIN_USER_RATINGS].index
    log(f"  {len(eligible):,} users have >= {MIN_USER_RATINGS} ratings on catalog movies")
    rng = np.random.default_rng(RANDOM_SEED)
    if n_users_cap is not None and len(eligible) > n_users_cap:
        eligible = pd.Index(rng.choice(eligible.to_numpy(), size=n_users_cap, replace=False))
    train_ratings = catalog_ratings[catalog_ratings["userId"].isin(eligible)].copy()
    log(f"  training on {len(train_ratings):,} ratings from {train_ratings.userId.nunique():,} users")

    stats = (
        catalog_ratings.groupby("movieId")
        .agg(avg_rating=("rating", "mean"), rating_count=("rating", "size"))
        .reset_index()
    )
    global_mean = float(catalog_ratings["rating"].mean())
    C = 80.0
    stats["bayes_avg"] = (C * global_mean + stats["rating_count"] * stats["avg_rating"]) / (
        C + stats["rating_count"]
    )

    log("Collecting top tags...")
    tags = pd.read_csv(TAGS_CSV, usecols=["movieId", "tag"])
    tags = tags[tags["movieId"].isin(keep)]
    tag_n = (
        tags.groupby(["movieId", "tag"], observed=True)
        .size()
        .reset_index(name="n")
        .sort_values(["movieId", "n"], ascending=[True, False])
        .groupby("movieId")
        .head(4)
    )
    tag_map = tag_n.groupby("movieId")["tag"].apply(lambda s: [str(x) for x in s]).to_dict()

    catalog = movies[movies["movieId"].isin(keep)].merge(stats, on="movieId", how="left")
    catalog = catalog.merge(links, on="movieId", how="left")
    catalog["avg_rating"] = catalog["avg_rating"].fillna(global_mean)
    catalog["rating_count"] = catalog["rating_count"].fillna(0).astype(int)
    catalog["bayes_avg"] = catalog["bayes_avg"].fillna(global_mean)
    catalog["tags"] = catalog["movieId"].map(lambda m: tag_map.get(int(m), []))
    catalog["imdbId"] = catalog["imdbId"].apply(
        lambda x: None if pd.isna(x) else f"{int(x):07d}"
    )
    catalog["tmdbId"] = catalog["tmdbId"].apply(lambda x: None if pd.isna(x) else int(x))
    catalog = catalog.set_index("movieId", drop=False)
    catalog.to_parquet(CATALOG_PATH)

    starters = pick_starters(catalog)
    STARTERS_PATH.write_text(json.dumps(starters), encoding="utf-8")

    log("Training LensKit ItemKNN pipeline...")
    from lenskit.data import from_interactions_df
    from lenskit.knn import ItemKNNScorer
    from lenskit.pipeline import topn_pipeline

    eval_n = min(80 if quick else 120, train_ratings.userId.nunique())
    eval_users = rng.choice(train_ratings["userId"].unique(), size=eval_n, replace=False)
    hold = (
        train_ratings[train_ratings["userId"].isin(eval_users)]
        .groupby("userId", group_keys=False)
        .sample(n=5, random_state=RANDOM_SEED)
    )
    fit = train_ratings.drop(index=hold.index)
    lk_df = fit.rename(columns={"userId": "user_id", "movieId": "item_id"})
    data = from_interactions_df(lk_df[["user_id", "item_id", "rating"]])
    pipe = topn_pipeline(
        ItemKNNScorer(k=KNN_NEIGHBORS, save_nbrs=SAVE_NBRS),
        n=80,
        predicts_ratings=True,
        name="later-itemknn",
    )
    t0 = time.time()
    pipe.train(data)
    log(f"  ItemKNN trained in {time.time() - t0:.1f}s")
    with PIPELINE_PATH.open("wb") as f:
        pickle.dump(pipe, f, protocol=5)
    log(f"  saved {PIPELINE_PATH.name} ({PIPELINE_PATH.stat().st_size / 1e6:.1f} MB)")

    metrics = evaluate_itemknn(pipe, fit, hold)
    metrics.update(
        {
            "catalog_movies": int(len(catalog)),
            "training_users": int(train_ratings.userId.nunique()),
            "training_ratings": int(len(train_ratings)),
            "catalog_ratings_scanned": int(n_catalog_ratings),
            "global_mean_rating": round(global_mean, 3),
            "timezone": RATING_TIMEZONE,
            "dataset": "MovieLens 32M (all movies with >=20 ratings, all eligible users)",
            "min_movie_ratings": MIN_MOVIE_RATINGS,
        }
    )
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    TRAIN_INFO_PATH.write_text(
        json.dumps(
            {
                "quick": quick,
                "full": not quick,
                "catalog_movies": int(len(catalog)),
                "n_users": None if n_users_cap is None else n_users_cap,
                "min_movie_ratings": MIN_MOVIE_RATINGS,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    log("Training complete.")
    log(json.dumps(metrics, indent=2))
    log("Running ranking evaluation (ImplicitMF + hybrid)...")
    from backend.evaluate import run as run_ranking_eval

    run_ranking_eval()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Smaller sample for a faster first run")
    args = parser.parse_args()
    train(quick=args.quick)

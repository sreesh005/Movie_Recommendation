"""Holdout eval: compare ItemKNN, popularity, hybrid, and ImplicitMF on the same 120 users.

Also trains ImplicitMF on liked ratings (>= 4) and saves it for the app.
"""

from __future__ import annotations

import json
import pickle
import time

import numpy as np
import pandas as pd

from backend.config import (
    ARTIFACTS,
    CATALOG_PATH,
    GENRE_ORDER,
    IMF_PATH,
    METRICS_PATH,
    MIN_USER_RATINGS,
    PIPELINE_PATH,
    RANDOM_SEED,
)

LIKED = 4.0
EVAL_N = 120
HOLD_N = 5
K = 20
CAND_N = 200


def log(msg: str) -> None:
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"), flush=True)


def _minmax(values: dict[int, float]) -> dict[int, float]:
    if not values:
        return {}
    nums = np.array(list(values.values()), dtype=float)
    lo, hi = float(nums.min()), float(nums.max())
    if hi - lo < 1e-9:
        return {k: 0.5 for k in values}
    return {k: (v - lo) / (hi - lo) for k, v in values.items()}


def _ndcg(recs: list[int], relevant: set[int], k: int = K) -> float:
    if not relevant:
        return 0.0
    dcg = 0.0
    for rank, item in enumerate(recs[:k], start=1):
        if item in relevant:
            dcg += 1.0 / np.log2(rank + 1)
    ideal = sum(1.0 / np.log2(i + 1) for i in range(1, min(len(relevant), k) + 1))
    return dcg / ideal if ideal else 0.0


def _recall(recs: list[int], relevant: set[int], k: int = K) -> float:
    if not relevant:
        return 0.0
    return len(set(recs[:k]) & relevant) / len(relevant)


def rebuild_split() -> tuple[pd.DataFrame, pd.DataFrame]:
    log("Loading catalog ratings and rebuilding the original 120-user holdout...")
    ratings = pd.read_parquet(ARTIFACTS / "catalog_ratings.parquet", columns=["userId", "movieId", "rating"])
    user_counts = ratings.groupby("userId").size()
    eligible = user_counts[user_counts >= MIN_USER_RATINGS].index
    train_ratings = ratings[ratings["userId"].isin(eligible)]
    rng = np.random.default_rng(RANDOM_SEED)
    eval_users = rng.choice(train_ratings["userId"].unique(), size=EVAL_N, replace=False)
    hold = (
        train_ratings[train_ratings["userId"].isin(eval_users)]
        .groupby("userId", group_keys=False)
        .sample(n=HOLD_N, random_state=RANDOM_SEED)
    )
    fit = train_ratings.drop(index=hold.index)
    log(f"  fit {len(fit):,} rows; hold {len(hold):,} rows; catalog movies later from parquet")
    return fit, hold


def load_catalog() -> pd.DataFrame:
    catalog = pd.read_parquet(CATALOG_PATH)
    if "movieId" not in catalog.columns:
        catalog = catalog.reset_index()
    catalog["movieId"] = catalog["movieId"].astype(int)
    return catalog.set_index("movieId", drop=False)


def genre_matrix(catalog: pd.DataFrame) -> tuple[np.ndarray, dict[int, int], list[int]]:
    ids = [int(i) for i in catalog.index]
    index = {mid: i for i, mid in enumerate(ids)}
    mat = np.zeros((len(ids), len(GENRE_ORDER)), dtype=np.float32)
    for mid, row in catalog.iterrows():
        genres = row["genres"]
        if isinstance(genres, str):
            genres = [g for g in genres.split("|") if g]
        for g in genres:
            if g in GENRE_ORDER:
                mat[index[int(mid)], GENRE_ORDER.index(g)] = 1.0
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms, index, ids


def content_scores(
    hist: dict[int, float],
    mat: np.ndarray,
    index: dict[int, int],
    ids: list[int],
) -> dict[int, float]:
    profile = np.zeros(mat.shape[1], dtype=np.float32)
    for mid, rating in hist.items():
        row = index.get(int(mid))
        if row is None:
            continue
        profile += (float(rating) - 3.0) * mat[row]
    norm = np.linalg.norm(profile)
    if norm:
        profile = profile / norm
    dots = mat @ profile
    return {mid: float(dots[i]) for i, mid in enumerate(ids) if mid not in hist}


def knn_scores(pipe, hist: dict[int, float], n: int = CAND_N) -> dict[int, float]:
    from lenskit.data import ItemList, RecQuery
    from lenskit.operations import recommend

    item_ids = [int(i) for i in hist]
    query = RecQuery(
        history_items=ItemList(item_ids, rating=[float(hist[i]) for i in item_ids])
    )
    recs = recommend(pipe, query, n=n)
    out: dict[int, float] = {}
    scores = recs.scores()
    for item_id, score in zip(recs.ids(), scores):
        mid = int(item_id)
        if mid in hist or score is None or (isinstance(score, float) and np.isnan(score)):
            continue
        out[mid] = float(score)
    return out


def hybrid_rank(
    hist: dict[int, float],
    knn: dict[int, float],
    content: dict[int, float],
    pop: dict[int, float],
    counts: dict[int, int],
    knn_pop: bool = False,
) -> list[int]:
    n_r = len(hist)
    if n_r == 0:
        w_knn, w_content, w_pop = 0.0, 0.0, 1.0
    elif n_r < 5:
        w_knn, w_content, w_pop = 0.35, 0.40, 0.25
    else:
        w_knn, w_content, w_pop = 0.62, 0.23, 0.15

    knn_use = knn
    if knn_pop and knn:
        knn_use = {mid: sc * np.log1p(counts.get(mid, 0)) for mid, sc in knn.items()}

    knn_n = _minmax(knn_use)
    content_n = _minmax({k: v for k, v in content.items() if k not in hist})
    pop_n = _minmax({k: v for k, v in pop.items() if k not in hist})

    cands = set(knn_n)
    cands |= set(sorted(content_n, key=content_n.get, reverse=True)[:120])
    cands |= set(sorted(pop_n, key=pop_n.get, reverse=True)[:200])
    cands -= set(hist)
    ranked = []
    for mid in cands:
        score = (
            w_knn * knn_n.get(mid, 0.0)
            + w_content * content_n.get(mid, 0.0)
            + w_pop * pop_n.get(mid, 0.0)
        )
        ranked.append((score, mid))
    ranked.sort(reverse=True)
    return [mid for _, mid in ranked[:K]]


def summarize(name: str, recs_by_user: dict[int, list[int]], hold: pd.DataFrame) -> dict:
    all_ndcg = []
    all_recall = []
    liked_ndcg = []
    liked_recall = []
    hits_all = 0
    total_all = 0
    hits_liked = 0
    total_liked = 0
    for uid, recs in recs_by_user.items():
        truth_df = hold[hold["userId"] == uid]
        truth = set(int(x) for x in truth_df["movieId"])
        liked = set(int(x) for x in truth_df.loc[truth_df["rating"] >= LIKED, "movieId"])
        all_ndcg.append(_ndcg(recs, truth))
        all_recall.append(_recall(recs, truth))
        hits_all += len(set(recs[:K]) & truth)
        total_all += len(truth)
        if liked:
            liked_ndcg.append(_ndcg(recs, liked))
            liked_recall.append(_recall(recs, liked))
            hits_liked += len(set(recs[:K]) & liked)
            total_liked += len(liked)
    metrics = {
        "algorithm": name,
        "users": len(recs_by_user),
        "recall_at_20": round(float(np.mean(all_recall)), 4) if all_recall else 0.0,
        "ndcg_at_20": round(float(np.mean(all_ndcg)), 4) if all_ndcg else 0.0,
        "hits": int(hits_all),
        "holdout_items": int(total_all),
        "liked_users": len(liked_ndcg),
        "liked_recall_at_20": round(float(np.mean(liked_recall)), 4) if liked_recall else 0.0,
        "liked_ndcg_at_20": round(float(np.mean(liked_ndcg)), 4) if liked_ndcg else 0.0,
        "liked_hits": int(hits_liked),
        "liked_holdout_items": int(total_liked),
    }
    log(
        f"  {name:22}  all nDCG={metrics['ndcg_at_20']:.4f} recall={metrics['recall_at_20']:.4f} "
        f"({metrics['hits']}/{metrics['holdout_items']})  |  liked nDCG={metrics['liked_ndcg_at_20']:.4f} "
        f"recall={metrics['liked_recall_at_20']:.4f} ({metrics['liked_hits']}/{metrics['liked_holdout_items']})"
    )
    return metrics


def train_implicit_mf(fit: pd.DataFrame):
    from lenskit.als import ImplicitMFScorer
    from lenskit.data import from_interactions_df
    from lenskit.pipeline import topn_pipeline

    liked = fit[fit["rating"] >= LIKED][["userId", "movieId"]].rename(
        columns={"userId": "user_id", "movieId": "item_id"}
    )
    log(f"Training ImplicitMF on {len(liked):,} liked ratings (rating >= {LIKED})...")
    t0 = time.time()
    data = from_interactions_df(liked)
    pipe = topn_pipeline(
        ImplicitMFScorer(embedding_size=64, epochs=10, weight=40, user_embeddings=False),
        n=CAND_N,
        predicts_ratings=False,
        name="later-implicit-mf",
    )
    pipe.train(data)
    log(f"  ImplicitMF trained in {time.time() - t0:.1f}s")
    IMF_PATH.parent.mkdir(exist_ok=True)
    with IMF_PATH.open("wb") as f:
        pickle.dump(pipe, f, protocol=5)
    log(f"  saved {IMF_PATH.name} ({IMF_PATH.stat().st_size / 1e6:.1f} MB)")
    return pipe


def run() -> dict:
    import lenskit.knn.item  # noqa: F401  needed to unpickle

    fit, hold = rebuild_split()
    catalog = load_catalog()
    mat, gindex, gids = genre_matrix(catalog)
    bayes = {int(i): float(catalog.loc[i, "bayes_avg"]) for i in catalog.index}
    counts = {int(i): int(catalog.loc[i, "rating_count"]) for i in catalog.index}
    pop = {mid: float(np.log1p(n)) for mid, n in counts.items()}
    bayes_order = sorted(bayes, key=bayes.get, reverse=True)
    count_order = sorted(counts, key=counts.get, reverse=True)

    log(f"Loading ItemKNN pipeline ({PIPELINE_PATH.name})...")
    with PIPELINE_PATH.open("rb") as f:
        knn_pipe = pickle.load(f)

    history = fit.groupby("userId")
    users = sorted(int(u) for u in hold["userId"].unique())

    knn20: dict[int, list[int]] = {}
    knn_count: dict[int, list[int]] = {}
    bayes20: dict[int, list[int]] = {}
    pop20: dict[int, list[int]] = {}
    hybrid: dict[int, list[int]] = {}
    hybrid_pop: dict[int, list[int]] = {}

    log(f"Scoring {len(users)} users (ItemKNN + hybrid)...")
    t0 = time.time()
    for i, uid in enumerate(users, start=1):
        try:
            hist_df = history.get_group(uid)
        except KeyError:
            continue
        hist = {int(m): float(r) for m, r in zip(hist_df["movieId"], hist_df["rating"])}
        knn = knn_scores(knn_pipe, hist, n=CAND_N)
        content = content_scores(hist, mat, gindex, gids)
        ranked_knn = sorted(knn, key=knn.get, reverse=True)
        knn20[uid] = ranked_knn[:K]
        knn_weighted = {mid: sc * np.log1p(counts.get(mid, 0)) for mid, sc in knn.items()}
        knn_count[uid] = sorted(knn_weighted, key=knn_weighted.get, reverse=True)[:K]
        bayes20[uid] = [mid for mid in bayes_order if mid not in hist][:K]
        pop20[uid] = [mid for mid in count_order if mid not in hist][:K]
        hybrid[uid] = hybrid_rank(hist, knn, content, pop, counts, knn_pop=False)
        hybrid_pop[uid] = hybrid_rank(hist, knn, content, pop, counts, knn_pop=True)
        if i % 20 == 0:
            log(f"  {i}/{len(users)} users ({time.time() - t0:.1f}s)")
    log(f"  ItemKNN/hybrid loop done in {time.time() - t0:.1f}s")

    results = [
        summarize("ItemKNN (original)", knn20, hold),
        summarize("ItemKNN x log-count", knn_count, hold),
        summarize("Popularity (Bayes)", bayes20, hold),
        summarize("Popularity (count)", pop20, hold),
        summarize("Hybrid (count pop)", hybrid, hold),
        summarize("Hybrid + pop-weighted KNN", hybrid_pop, hold),
    ]

    imf_pipe = train_implicit_mf(fit)
    imf20: dict[int, list[int]] = {}
    hybrid_imf: dict[int, list[int]] = {}
    log("Scoring ImplicitMF...")
    t0 = time.time()
    for i, uid in enumerate(users, start=1):
        try:
            hist_df = history.get_group(uid)
        except KeyError:
            continue
        hist = {int(m): float(r) for m, r in zip(hist_df["movieId"], hist_df["rating"])}
        liked_hist = {m: r for m, r in hist.items() if r >= LIKED} or hist
        imf = knn_scores(imf_pipe, liked_hist, n=CAND_N)
        content = content_scores(hist, mat, gindex, gids)
        ranked = sorted(imf, key=imf.get, reverse=True)
        imf20[uid] = ranked[:K]
        hybrid_imf[uid] = hybrid_rank(hist, imf, content, pop, counts, knn_pop=True)
        if i % 20 == 0:
            log(f"  {i}/{len(users)} IMF users ({time.time() - t0:.1f}s)")
    log(f"  ImplicitMF loop done in {time.time() - t0:.1f}s")
    results.append(summarize("ImplicitMF (liked)", imf20, hold))
    results.append(summarize("Hybrid + ImplicitMF", hybrid_imf, hold))

    catalog_n = int(len(catalog))
    random_recall = round(K / catalog_n, 5)
    best = max(results, key=lambda m: m["ndcg_at_20"])
    original = next(m for m in results if m["algorithm"] == "ItemKNN (original)")
    payload = {
        "users_evaluated": EVAL_N,
        "holdout_items_per_user": HOLD_N,
        "catalog_movies": catalog_n,
        "recall_at_20": best["recall_at_20"],
        "ndcg_at_20": best["ndcg_at_20"],
        "algorithm": best["algorithm"],
        "relevance_threshold": LIKED,
        "random_recall_at_20": random_recall,
        "baseline_itemknn": original,
        "best": best,
        "all": results,
        "note": (
            "Headline recall/nDCG use the original protocol (all 5 random holdouts). "
            "liked_* metrics count only hidden ratings >= 4. "
            "ItemKNN predicted-rating ranking was 0.0058 nDCG@20; the live ranker uses the best algorithm."
        ),
    }
    if METRICS_PATH.exists():
        try:
            previous = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
            for key in (
                "training_users",
                "training_ratings",
                "catalog_ratings_scanned",
                "global_mean_rating",
                "timezone",
                "dataset",
                "min_movie_ratings",
            ):
                if key in previous and key not in payload:
                    payload[key] = previous[key]
        except (json.JSONDecodeError, TypeError):
            pass
    METRICS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    log(f"Wrote {METRICS_PATH}")
    log(json.dumps({"best": best, "baseline": original}, indent=2))
    return payload


if __name__ == "__main__":
    run()

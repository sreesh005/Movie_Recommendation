"""RMSE and like/dislike accuracy on the same holdout as evaluate.py.

RMSE uses ItemKNN (ImplicitMF only ranks, no star predictions).
Like accuracy = logistic regression on rating >= 4.
"""

from __future__ import annotations

import json
import pickle
import time

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from backend.config import ARTIFACTS, METRICS_PATH, PIPELINE_PATH
from backend.evaluate import (
    EVAL_N,
    HOLD_N,
    genre_matrix,
    load_catalog,
    log,
    rebuild_split,
)

LIKE_PATH = ARTIFACTS / "like_classifier.pkl"
LIKE_THRESHOLD = 4.0


def _rmse(y: np.ndarray, yhat: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y - yhat) ** 2)))


def _mae(y: np.ndarray, yhat: np.ndarray) -> float:
    return float(np.mean(np.abs(y - yhat)))


def _binary(y_true_like: np.ndarray, y_pred_like: np.ndarray) -> dict:
    tp = int(np.sum(y_true_like & y_pred_like))
    tn = int(np.sum(~y_true_like & ~y_pred_like))
    fp = int(np.sum(~y_true_like & y_pred_like))
    fn = int(np.sum(y_true_like & ~y_pred_like))
    n = max(tp + tn + fp + fn, 1)
    return {
        "accuracy": round((tp + tn) / n, 4),
        "precision": round(tp / (tp + fp), 4) if tp + fp else 0.0,
        "recall": round(tp / (tp + fn), 4) if tp + fn else 0.0,
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "n": n,
    }


def _user_profile(hist: dict[int, float], mat: np.ndarray, index: dict[int, int]) -> np.ndarray:
    profile = np.zeros(mat.shape[1], dtype=np.float32)
    for mid, rating in hist.items():
        row = index.get(int(mid))
        if row is None:
            continue
        profile += (float(rating) - 3.0) * mat[row]
    norm = np.linalg.norm(profile)
    if norm:
        profile = profile / norm
    return profile


def _features(
    hist: dict[int, float],
    mid: int,
    profile: np.ndarray,
    bayes: dict[int, float],
    counts: dict[int, int],
    mat: np.ndarray,
    index: dict[int, int],
    user_mean: float,
) -> list[float]:
    row = index.get(int(mid))
    cosine = float(profile @ mat[row]) if row is not None else 0.0
    return [
        user_mean,
        float(bayes.get(int(mid), 3.5)),
        float(np.log1p(counts.get(int(mid), 0))),
        cosine,
    ]


def knn_predict_holdout(pipe, hist: dict[int, float], item_ids: list[int]) -> dict[int, float]:
    from lenskit.data import ItemList, RecQuery
    from lenskit.operations import predict

    query = RecQuery(
        history_items=ItemList(
            [int(i) for i in hist],
            rating=[float(hist[i]) for i in hist],
        )
    )
    preds = predict(pipe, query, items=ItemList([int(i) for i in item_ids]))
    out: dict[int, float] = {}
    scores = preds.scores()
    for item_id, score in zip(preds.ids(), scores):
        if score is None or (isinstance(score, float) and np.isnan(score)):
            continue
        out[int(item_id)] = float(np.clip(score, 0.5, 5.0))
    return out


def run() -> dict:
    import lenskit.knn.item  # noqa: F401

    fit, hold = rebuild_split()
    catalog = load_catalog()
    mat, gindex, _gids = genre_matrix(catalog)
    bayes = {int(i): float(catalog.loc[i, "bayes_avg"]) for i in catalog.index}
    counts = {int(i): int(catalog.loc[i, "rating_count"]) for i in catalog.index}
    global_mean = float(fit["rating"].mean())

    log(f"Loading ItemKNN rating predictor ({PIPELINE_PATH.name})...")
    with PIPELINE_PATH.open("rb") as f:
        knn_pipe = pickle.load(f)

    history = fit.groupby("userId")
    users = sorted(int(u) for u in hold["userId"].unique())

    y_true: list[float] = []
    y_knn: list[float] = []
    y_user: list[float] = []
    y_item: list[float] = []
    y_global: list[float] = []
    test_X: list[list[float]] = []
    test_y: list[int] = []
    train_X: list[list[float]] = []
    train_y: list[int] = []

    log(f"Predicting {len(users)} users x {HOLD_N} holdout ratings...")
    t0 = time.time()
    missing_knn = 0
    for i, uid in enumerate(users, start=1):
        try:
            hist_df = history.get_group(uid)
        except KeyError:
            continue
        hist = {int(m): float(r) for m, r in zip(hist_df["movieId"], hist_df["rating"])}
        user_mean = float(np.mean(list(hist.values()))) if hist else global_mean
        profile = _user_profile(hist, mat, gindex)
        truth_df = hold[hold["userId"] == uid]
        item_ids = [int(m) for m in truth_df["movieId"]]
        preds = knn_predict_holdout(knn_pipe, hist, item_ids)

        for mid, rating in zip(truth_df["movieId"], truth_df["rating"]):
            mid = int(mid)
            actual = float(rating)
            knn_hat = preds.get(mid)
            if knn_hat is None:
                missing_knn += 1
                knn_hat = float(np.clip(user_mean, 0.5, 5.0))
            y_true.append(actual)
            y_knn.append(knn_hat)
            y_user.append(user_mean)
            y_item.append(float(np.clip(bayes.get(mid, global_mean), 0.5, 5.0)))
            y_global.append(global_mean)
            test_X.append(_features(hist, mid, profile, bayes, counts, mat, gindex, user_mean))
            test_y.append(1 if actual >= LIKE_THRESHOLD else 0)

        sample = hist_df
        if len(sample) > 80:
            sample = sample.sample(n=80, random_state=42)
        for mid, rating in zip(sample["movieId"], sample["rating"]):
            mid = int(mid)
            train_X.append(_features(hist, mid, profile, bayes, counts, mat, gindex, user_mean))
            train_y.append(1 if float(rating) >= LIKE_THRESHOLD else 0)

        if i % 20 == 0:
            log(f"  {i}/{len(users)} users ({time.time() - t0:.1f}s)")

    y = np.array(y_true, dtype=float)
    like = y >= LIKE_THRESHOLD
    majority = bool(np.mean(like) >= 0.5)

    knn = np.array(y_knn, dtype=float)
    user = np.array(y_user, dtype=float)
    item = np.array(y_item, dtype=float)
    glob = np.array(y_global, dtype=float)

    rating_rows = {
        "ItemKNN rating predictor": knn,
        "User mean": user,
        "Item Bayesian average": item,
        "Global mean": glob,
    }
    rating_table = []
    for name, yhat in rating_rows.items():
        row = {
            "model": name,
            "rmse": round(_rmse(y, yhat), 4),
            "mae": round(_mae(y, yhat), 4),
            **{f"like_{k}": v for k, v in _binary(like, yhat >= LIKE_THRESHOLD).items()},
        }
        rating_table.append(row)
        log(
            f"  {name:28} RMSE={row['rmse']:.4f} MAE={row['mae']:.4f} "
            f"like-accuracy={row['like_accuracy']:.4f}"
        )

    log(f"Training like/dislike logistic regression on {len(train_X):,} history ratings...")
    clf = Pipeline(
        [
            ("scale", StandardScaler()),
            ("lr", LogisticRegression(max_iter=400, class_weight="balanced")),
        ]
    )
    clf.fit(np.array(train_X, dtype=float), np.array(train_y, dtype=int))
    proba = clf.predict_proba(np.array(test_X, dtype=float))[:, 1]
    pred_like = proba >= 0.5
    like_metrics = _binary(np.array(test_y, dtype=bool), pred_like)
    like_metrics.update(
        {
            "model": "Logistic regression (like if rating >= 4)",
            "features": ["user_mean", "item_bayes_avg", "log_rating_count", "genre_cosine"],
            "train_rows": len(train_X),
            "test_rows": len(test_X),
            "threshold": LIKE_THRESHOLD,
            "mean_predicted_like_probability": round(float(np.mean(proba)), 4),
        }
    )
    log(
        f"  Logistic like-accuracy={like_metrics['accuracy']:.4f} "
        f"precision={like_metrics['precision']:.4f} recall={like_metrics['recall']:.4f} "
        f"({like_metrics['true_positive']}+{like_metrics['true_negative']}/"
        f"{like_metrics['n']})"
    )

    majority_acc = round(float(np.mean(like) if majority else 1.0 - np.mean(like)), 4)
    WITH_KNN = next(r for r in rating_table if r["model"].startswith("ItemKNN"))

    payload = {
        "protocol": (
            f"Same {EVAL_N}-user seed-42 holdout as ranking ({HOLD_N} ratings/user, "
            f"{len(y)} stars). RMSE is star-prediction error. ImplicitMF is ranking-only "
            "and is not scored with RMSE. Like-accuracy treats rating>=4 as the positive class."
        ),
        "holdout_ratings": int(len(y)),
        "liked_holdout_share": round(float(np.mean(like)), 4),
        "majority_class_accuracy": majority_acc,
        "knn_fallback_to_user_mean": int(missing_knn),
        "rmse": WITH_KNN["rmse"],
        "mae": WITH_KNN["mae"],
        "like_accuracy_itemknn": WITH_KNN["like_accuracy"],
        "like_accuracy_logistic": like_metrics["accuracy"],
        "rating_models": rating_table,
        "like_classifier": like_metrics,
    }

    LIKE_PATH.parent.mkdir(exist_ok=True)
    with LIKE_PATH.open("wb") as f:
        pickle.dump({"pipeline": clf, "features": like_metrics["features"]}, f, protocol=5)
    log(f"  saved {LIKE_PATH.name}")

    if METRICS_PATH.exists():
        metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    else:
        metrics = {}
    metrics["rmse"] = payload["rmse"]
    metrics["mae"] = payload["mae"]
    metrics["like_accuracy"] = payload["like_accuracy_logistic"]
    metrics["rating_prediction"] = payload
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    log(f"Wrote {METRICS_PATH}")
    log(json.dumps({"rmse": payload["rmse"], "mae": payload["mae"], "like_accuracy": payload["like_accuracy_logistic"]}, indent=2))
    return payload


if __name__ == "__main__":
    run()

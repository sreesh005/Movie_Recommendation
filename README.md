# Later

A MovieLens 32M recommender built with LensKit: ImplicitMF + genre + popularity, mood rows, and a “when to watch” suggestion.

## Data

Download [MovieLens 32M](https://grouplens.org/datasets/movielens/32m/) and put `ratings.csv`, `movies.csv`, `tags.csv`, and `links.csv` in the project root. The data isn't in the repo (too big, and the license doesn't allow redistribution).

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
python -m backend.train
cd frontend
npm install
npm run dev
```

In a second terminal, from the project root:

```powershell
.\.venv\Scripts\python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Open [http://localhost:5173](http://localhost:5173). The first training pass reads the 32M ratings file and can take 10–20 minutes.

Use `python -m backend.train --quick` only for a smoke test.

Poster art comes from the TMDB API. Put a free key in `.env` as `TMDB_API_KEY=...` (or `TMDB_READ_ACCESS_TOKEN`), then:

```powershell
.\.venv\Scripts\python -m backend.fetch_posters
```

The UI reads `artifacts/posters.json` and falls back to a title card when a film has no art.

## Algorithm

1. Keep movies with at least 20 ratings (23,350 movies, 200,763 users, 31.7M ratings).
2. Train ItemKNN (star predictions) and ImplicitMF on liked ratings (4+ stars).
3. At request time, blend ImplicitMF × log rating count, genre cosine, and popularity. Weights shift toward ImplicitMF as the user rates more movies.
4. Watch windows come from genre rules plus rating-hour/day histograms in America/Chicago.

## Results (120-user holdout, 5 hidden ratings each)

| Model | nDCG@20 | Recall@20 | Hits / 600 |
|---|---|---|---|
| ItemKNN (predicted stars) | 0.0058 | 0.0067 | 4 |
| Hybrid + ImplicitMF (live) | 0.2037 | 0.2783 | 167 |

ItemKNN star RMSE is 0.861. A logistic like/dislike classifier gets 70.5% accuracy (52.7% baseline).

`python -m backend.evaluate` and `python -m backend.rating_eval` rerun the holdout and write `artifacts/metrics.json`.

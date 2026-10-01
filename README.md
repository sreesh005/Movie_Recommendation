# Later

A MovieLens 32M recommender: LensKit item–item collaborative filtering, plus genre taste and a “when to watch” suggestion.

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

1. Keep the 5,000 most-rated movies, then sample 12,000 users with at least 20 ratings.
2. Train LensKit `ItemKNNScorer` (explicit item–item CF) and pickle the pipeline.
3. At request time, blend KNN predicted ratings with genre cosine (content) and a Bayesian popularity prior.
4. Watch windows combine genre heuristics with MovieLens rating-hour/day histograms in America/Chicago.

Cite in the report: Harper & Konstan (2015) MovieLens; Ekstrand (2020) LensKit; Linden et al. Amazon item-to-item CF; MovieLens.org / Netflix / Letterboxd as UI references.

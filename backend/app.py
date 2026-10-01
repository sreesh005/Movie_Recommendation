from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.config import MOODS, ROOT
from backend.recommender import get_engine

app = FastAPI(title="Later", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RecommendRequest(BaseModel):
    ratings: dict[str, float] = Field(default_factory=dict)
    mood: str | None = None
    hour: int | None = None
    weekday: int | None = None
    n: int = 40


def engine_or_503():
    engine = get_engine()
    if not engine.ready:
        raise HTTPException(status_code=503, detail=engine.error or "Recommender is not ready")
    return engine


@app.get("/api/health")
def health():
    engine = get_engine()
    if engine.ready:
        engine.refresh_posters()
    posters = sum(1 for movie in engine.movies.values() if movie.poster_url)
    return {
        "ready": engine.ready,
        "error": engine.error,
        "movies": len(engine.movies),
        "posters": posters,
    }


@app.get("/api/moods")
def moods():
    return MOODS


@app.get("/api/metrics")
def metrics():
    engine = engine_or_503()
    return engine.metrics


@app.get("/api/starters")
def starters():
    engine = engine_or_503()
    return engine.starter_movies()


@app.get("/api/search")
def search(q: str = "", limit: int = 24):
    engine = engine_or_503()
    return engine.search(q, limit=min(limit, 48))


@app.get("/api/movies/{movie_id}")
def movie(movie_id: int):
    engine = engine_or_503()
    payload = engine.movie_public(movie_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Movie not in catalog")
    return payload


@app.post("/api/recommend")
def recommend(body: RecommendRequest):
    engine = engine_or_503()
    ratings = {int(k): float(v) for k, v in body.ratings.items() if float(v) > 0}
    mood = body.mood if body.mood in {m["id"] for m in MOODS} else None
    hour = body.hour if body.hour is not None and 0 <= body.hour <= 23 else None
    weekday = body.weekday if body.weekday is not None and 0 <= body.weekday <= 6 else None
    return engine.recommend(ratings, mood=mood, hour=hour, weekday=weekday, n=min(body.n, 80))


dist = ROOT / "frontend" / "dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=dist, html=True), name="ui")

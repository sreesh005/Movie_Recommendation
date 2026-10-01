"""Fetch TMDB poster URLs for every catalog movie and cache them locally."""

from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests

from backend.config import ARTIFACTS, CATALOG_PATH, POSTERS_PATH, ROOT, TMDB_IMAGE_BASE

TMDB_MOVIE_URL = "https://api.themoviedb.org/3/movie/{tmdb_id}"
WORKERS = 10
_THREAD = threading.local()


def load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def auth() -> tuple[dict, dict]:
    load_dotenv()
    token = os.environ.get("TMDB_READ_ACCESS_TOKEN") or os.environ.get("TMDB_ACCESS_TOKEN")
    api_key = os.environ.get("TMDB_API_KEY")
    headers = {"Accept": "application/json"}
    params: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif api_key:
        params["api_key"] = api_key
    else:
        raise SystemExit(
            "Set TMDB_API_KEY or TMDB_READ_ACCESS_TOKEN in the environment or a .env file.\n"
            "Create a free key at https://www.themoviedb.org/settings/api"
        )
    return headers, params


def load_existing() -> dict[str, str]:
    if not POSTERS_PATH.exists():
        return {}
    data = json.loads(POSTERS_PATH.read_text(encoding="utf-8"))
    return {str(k): v for k, v in data.items() if v}


def save(posters: dict[str, str]) -> None:
    ARTIFACTS.mkdir(exist_ok=True)
    POSTERS_PATH.write_text(json.dumps(posters, indent=2), encoding="utf-8")


def thread_session() -> requests.Session:
    session = getattr(_THREAD, "session", None)
    if session is None:
        session = requests.Session()
        _THREAD.session = session
    return session


def fetch_one(tmdb_id: int, headers: dict, params: dict) -> str | None:
    url = TMDB_MOVIE_URL.format(tmdb_id=int(tmdb_id))
    session = thread_session()
    for attempt in range(6):
        try:
            response = session.get(url, headers=headers, params=params, timeout=20)
        except requests.RequestException:
            time.sleep(0.4 * (attempt + 1))
            continue
        if response.status_code == 429:
            wait = float(response.headers.get("Retry-After", 1.5))
            time.sleep(wait)
            continue
        if response.status_code == 404:
            return None
        if response.status_code >= 500:
            time.sleep(0.5 * (attempt + 1))
            continue
        response.raise_for_status()
        poster_path = response.json().get("poster_path")
        if not poster_path:
            return None
        return f"{TMDB_IMAGE_BASE}{poster_path}"
    return None


def main() -> None:
    if not CATALOG_PATH.exists():
        raise SystemExit("Catalog missing. Run python -m backend.train first.")
    headers, params = auth()
    catalog = pd.read_parquet(CATALOG_PATH, columns=["movieId", "tmdbId"])
    posters = load_existing()
    pending: list[tuple[int, int]] = []
    for _, row in catalog.iterrows():
        movie_id = int(row["movieId"])
        if str(movie_id) in posters:
            continue
        if pd.isna(row["tmdbId"]):
            continue
        pending.append((movie_id, int(row["tmdbId"])))

    print(f"Already cached: {len(posters):,}")
    print(f"Need TMDB lookups: {len(pending):,}")
    if not pending:
        print(f"Wrote {POSTERS_PATH}")
        return

    fetched = 0
    missing = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {
            pool.submit(fetch_one, tmdb_id, headers, params): movie_id
            for movie_id, tmdb_id in pending
        }
        for i, future in enumerate(as_completed(futures), start=1):
            movie_id = futures[future]
            try:
                url = future.result()
            except Exception as exc:
                print(f"  failed movie {movie_id}: {exc}")
                url = None
            if url:
                posters[str(movie_id)] = url
                fetched += 1
            else:
                missing += 1
            if i % 250 == 0 or i == len(futures):
                save(posters)
                print(f"  {i:,}/{len(futures):,}  saved={len(posters):,}  missing={missing:,}")

    save(posters)
    print(f"Done. {fetched:,} new posters, {len(posters):,} total, {missing:,} without art.")
    print("This product uses the TMDB API but is not endorsed or certified by TMDB.")


if __name__ == "__main__":
    main()

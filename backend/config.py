from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"

RATINGS_CSV = ROOT / "ratings.csv"
MOVIES_CSV = ROOT / "movies.csv"
LINKS_CSV = ROOT / "links.csv"
TAGS_CSV = ROOT / "tags.csv"

N_MOVIES = 5000
N_USERS = 12000
MIN_USER_RATINGS = 20
KNN_NEIGHBORS = 20
SAVE_NBRS = 50
RANDOM_SEED = 42
RATING_TIMEZONE = "America/Chicago"

CATALOG_PATH = ARTIFACTS / "catalog.parquet"
STARTERS_PATH = ARTIFACTS / "starters.json"
WATCH_PATH = ARTIFACTS / "watch_windows.json"
METRICS_PATH = ARTIFACTS / "metrics.json"
PIPELINE_PATH = ARTIFACTS / "itemknn_pipeline.pkl"
TRAIN_INFO_PATH = ARTIFACTS / "train_info.json"
POSTERS_PATH = ARTIFACTS / "posters.json"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w342"

GENRE_PRIORITY = [
    "Horror",
    "Children",
    "Animation",
    "Documentary",
    "Romance",
    "Musical",
    "Film-Noir",
    "War",
    "Western",
    "Sci-Fi",
    "Fantasy",
    "Mystery",
    "Crime",
    "Thriller",
    "Action",
    "Adventure",
    "Comedy",
    "Drama",
]

WATCH_RULES = {
    "Horror": {"slot": "Friday night", "when": "After 8pm", "hours": list(range(20, 24)), "dows": [4, 5], "moods": ["scary", "tonight"]},
    "Thriller": {"slot": "Friday night", "when": "After 9pm", "hours": list(range(21, 24)), "dows": [4, 5], "moods": ["scary", "thrills", "tonight"]},
    "Children": {"slot": "Weekend afternoon", "when": "Saturday 1–4pm", "hours": list(range(13, 17)), "dows": [5, 6], "moods": ["family"]},
    "Animation": {"slot": "Weekend afternoon", "when": "Saturday 1–4pm", "hours": list(range(13, 17)), "dows": [5, 6], "moods": ["family", "comfort"]},
    "Romance": {"slot": "Saturday evening", "when": "Date night around 8pm", "hours": list(range(19, 23)), "dows": [5], "moods": ["date"]},
    "Comedy": {"slot": "Weeknight", "when": "Unwind after 7pm", "hours": list(range(19, 23)), "dows": [0, 1, 2, 3], "moods": ["comfort", "tonight"]},
    "Drama": {"slot": "Sunday evening", "when": "When you can pay attention", "hours": list(range(19, 22)), "dows": [6], "moods": ["date"]},
    "Action": {"slot": "Saturday night", "when": "Prime time 8pm", "hours": list(range(20, 23)), "dows": [5], "moods": ["thrills"]},
    "Adventure": {"slot": "Saturday night", "when": "Prime time 8pm", "hours": list(range(20, 23)), "dows": [5], "moods": ["thrills", "family"]},
    "Sci-Fi": {"slot": "Saturday night", "when": "Lights down after 8pm", "hours": list(range(20, 23)), "dows": [5], "moods": ["thrills"]},
    "Fantasy": {"slot": "Weekend evening", "when": "Saturday around 7pm", "hours": list(range(18, 22)), "dows": [5, 6], "moods": ["family", "comfort"]},
    "Documentary": {"slot": "Sunday morning", "when": "Coffee and a documentary", "hours": list(range(9, 13)), "dows": [6], "moods": ["comfort"]},
    "Musical": {"slot": "Weekend matinee", "when": "Sunday afternoon", "hours": list(range(13, 17)), "dows": [6], "moods": ["comfort", "family"]},
    "War": {"slot": "Sunday evening", "when": "When you can sit with it", "hours": list(range(19, 22)), "dows": [6], "moods": ["date"]},
    "Film-Noir": {"slot": "Late night", "when": "After 10pm", "hours": list(range(22, 24)) + [0], "dows": [4, 5], "moods": ["tonight"]},
    "Mystery": {"slot": "Weeknight", "when": "Lights down after 9pm", "hours": list(range(21, 24)), "dows": [1, 2, 3], "moods": ["tonight", "scary"]},
    "Crime": {"slot": "Friday night", "when": "After 9pm", "hours": list(range(21, 24)), "dows": [4, 5], "moods": ["scary", "thrills"]},
    "Western": {"slot": "Sunday afternoon", "when": "Slow afternoon", "hours": list(range(14, 18)), "dows": [6], "moods": ["comfort"]},
}

MOOD_GENRES = {
    "tonight": None,
    "date": {"Romance", "Drama"},
    "family": {"Children", "Animation"},
    "scary": {"Horror", "Thriller"},
    "comfort": {"Comedy", "Musical", "Animation", "Fantasy"},
    "thrills": {"Action", "Adventure", "Sci-Fi", "Thriller"},
}

MOODS = [
    {"id": "tonight", "label": "Tonight"},
    {"id": "date", "label": "Date night"},
    {"id": "family", "label": "Family"},
    {"id": "scary", "label": "Scary"},
    {"id": "comfort", "label": "Comfort"},
    {"id": "thrills", "label": "Thrills"},
]

STARTER_MUST_IDS = [
    1, 318, 296, 356, 260, 2571, 79132, 2959, 4993, 58559, 1196, 1198,
    858, 1221, 50, 527, 593, 2028, 7153, 4226, 1136, 608, 47, 2858,
    109487, 44191, 89745, 60069, 68954, 5618, 1704, 1193, 912, 750,
    904, 908, 1203, 1222, 1213, 1089, 111, 924, 541, 1200, 1214, 32,
    4878, 7361, 4973, 2324, 3147, 778, 1258, 1208, 1228, 1247,
]

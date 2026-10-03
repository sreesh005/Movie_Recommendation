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
MIN_MOVIE_RATINGS = 20
KNN_NEIGHBORS = 20
SAVE_NBRS = 50
RANDOM_SEED = 42
RATING_TIMEZONE = "America/Chicago"

CATALOG_PATH = ARTIFACTS / "catalog.parquet"
STARTERS_PATH = ARTIFACTS / "starters.json"
WATCH_PATH = ARTIFACTS / "watch_windows.json"
METRICS_PATH = ARTIFACTS / "metrics.json"
PIPELINE_PATH = ARTIFACTS / "itemknn_pipeline.pkl"
IMF_PATH = ARTIFACTS / "implicit_mf_pipeline.pkl"
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
    "date": {"Romance"},
    "family": {"Children"},
    "scary": {"Horror"},
    "comfort": {"Comedy", "Musical"},
    "thrills": {"Action", "Adventure", "Sci-Fi"},
}

MOOD_SEED_GENRES = {
    "date": ["Romance"],
    "family": ["Children", "Animation"],
    "scary": ["Horror"],
    "comfort": ["Comedy", "Musical", "Western"],
    "thrills": ["Action", "Adventure", "Sci-Fi"],
    "easy": ["Comedy", "Animation", "Adventure", "Fantasy", "Musical"],
    "focus": ["Drama", "Mystery", "Documentary", "Crime", "War"],
    "indie": [],
    "niche": [],
    "foreign": [],
    "tonight": [],
}

MOOD_GENRE_ROWS = {
    "date": ["Romance", "Comedy"],
    "family": ["Children", "Animation", "Adventure", "Fantasy"],
    "scary": ["Horror", "Mystery"],
    "comfort": ["Comedy", "Musical", "Western", "Animation"],
    "thrills": ["Action", "Adventure", "Sci-Fi"],
    "easy": ["Comedy", "Animation", "Adventure", "Fantasy", "Musical"],
    "focus": ["Drama", "Mystery", "Documentary", "Crime", "War", "Film-Noir"],
    "indie": ["Drama", "Comedy", "Documentary"],
    "niche": ["Drama", "Mystery", "Film-Noir", "Documentary"],
    "foreign": ["Drama", "Animation", "Crime", "Romance"],
}

HEAVY_GENRES = frozenset({"Horror", "Thriller", "Crime", "War", "Film-Noir"})

DARK_TAG_NEEDLES = (
    "disturbing",
    "dark comedy",
    "black comedy",
    "violence",
    "violent",
    "brutal",
    "gore",
    "gory",
    "torture",
    "rape",
    "suicide",
    "depressing",
    "bleak",
    "grim",
    "serial killer",
    "social thriller",
    "class warfare",
    "poverty",
    "cannibal",
    "slasher",
    "demonic",
    "possession",
    "holocaust",
    "nazi",
)

WARM_TAG_NEEDLES = (
    "feel-good",
    "feel good",
    "heartwarming",
    "whimsical",
    "quirky",
    "cute",
    "charming",
    "uplifting",
    "family",
)

EASY_TAG_NEEDLES = (
    "feel-good",
    "feel good",
    "funny",
    "silly",
    "goofy",
    "light",
    "popcorn",
    "mindless",
    "campy",
    "slapstick",
    "cheesy",
    "whimsical",
    "cute",
    "marvel",
    "pixar",
)

FOCUS_TAG_NEEDLES = (
    "thought-provoking",
    "thought provoking",
    "twist",
    "nonlinear",
    "non-linear",
    "complex",
    "cerebral",
    "philosophical",
    "psychological",
    "mind-bending",
    "mindbending",
    "slow burn",
    "slow-burn",
    "social commentary",
    "political",
    "existential",
    "character study",
    "courtroom",
    "meditation",
)

ADULT_TAG_NEEDLES = (
    "nudity",
    "sex",
    "sexual",
    "erotic",
    "raunchy",
    "crude",
    "drugs",
    "marijuana",
    "porn",
    "adult animation",
    "profanity",
)

SCARY_TAG_NEEDLES = (
    "horror",
    "creepy",
    "slasher",
    "ghost",
    "haunted",
    "demonic",
    "possession",
    "vampire",
    "zombie",
    "werewolf",
)

FOREIGN_TAG_TOKENS = frozenset(
    {
        "french",
        "korean",
        "japanese",
        "italian",
        "spanish",
        "german",
        "swedish",
        "danish",
        "norwegian",
        "finnish",
        "russian",
        "polish",
        "czech",
        "iranian",
        "persian",
        "chinese",
        "mandarin",
        "cantonese",
        "thai",
        "bollywood",
        "mexican",
        "brazilian",
        "argentine",
        "turkish",
        "greek",
        "hungarian",
        "romanian",
        "israeli",
        "arabic",
        "chilean",
        "portuguese",
        "belgian",
        "dutch",
        "austrian",
        "anime",
        "foreign",
    }
)

FOREIGN_TAG_NEEDLES = (
    "foreign",
    "world cinema",
    "hong kong",
    "south korean",
    "korean cinema",
    "japanese cinema",
    "french cinema",
    "italian cinema",
    "studio ghibli",
    "wong kar-wai",
    "cinema of",
)

INDIE_TAG_NEEDLES = (
    "independent",
    "indie",
    "sundance",
    "mumblecore",
    "low budget",
    "low-budget",
    "film festival",
    "criterion",
)

NICHE_TAG_NEEDLES = (
    "cult",
    "arthouse",
    "art-house",
    "art house",
    "avant-garde",
    "experimental",
    "underground",
    "midnight movie",
    "obscure",
)

FOREIGN_MUST_IDS = {
    202439,  # Parasite (2019)
    92259,  # Intouchables
    193065,  # Roma
    188773,  # Shoplifters
    257037,  # Drive My Car
    275167,  # Decision to Leave
    107314,  # Oldboy (2013)
}

FOREIGN_MUST_LANGS = {
    202439: "Korean",
    92259: "French",
    193065: "Spanish",
    188773: "Japanese",
    257037: "Japanese",
    275167: "Korean",
    107314: "Korean",
}

TOKEN_TO_LANGUAGE = {
    "french": "French",
    "korean": "Korean",
    "japanese": "Japanese",
    "anime": "Japanese",
    "italian": "Italian",
    "spanish": "Spanish",
    "german": "German",
    "swedish": "Swedish",
    "danish": "Danish",
    "norwegian": "Norwegian",
    "finnish": "Finnish",
    "russian": "Russian",
    "polish": "Polish",
    "czech": "Czech",
    "iranian": "Persian",
    "persian": "Persian",
    "chinese": "Chinese",
    "mandarin": "Chinese",
    "cantonese": "Chinese",
    "thai": "Thai",
    "bollywood": "Hindi",
    "mexican": "Spanish",
    "brazilian": "Portuguese",
    "argentine": "Spanish",
    "chilean": "Spanish",
    "portuguese": "Portuguese",
    "turkish": "Turkish",
    "greek": "Greek",
    "hungarian": "Hungarian",
    "romanian": "Romanian",
    "israeli": "Hebrew",
    "arabic": "Arabic",
    "belgian": "French",
    "dutch": "Dutch",
    "austrian": "German",
}

NEEDLE_TO_LANGUAGE = {
    "hong kong": "Chinese",
    "south korean": "Korean",
    "korean cinema": "Korean",
    "japanese cinema": "Japanese",
    "french cinema": "French",
    "italian cinema": "Italian",
    "studio ghibli": "Japanese",
    "wong kar-wai": "Chinese",
}

TITLE_TO_LANGUAGE = {
    "kamikakushi": "Japanese",
    "shichinin": "Japanese",
    "mononoke": "Japanese",
    "hauru": "Japanese",
    "sen to chihiro": "Japanese",
    "cidade": "Portuguese",
    "laberinto": "Spanish",
    "vita è": "Italian",
    "vita e bella": "Italian",
    "amélie": "French",
    "amelie": "French",
    "intouchables": "French",
    "das leben": "German",
    "le fabuleux": "French",
}

LANGUAGE_ORDER = [
    "Japanese",
    "Korean",
    "French",
    "Italian",
    "Spanish",
    "German",
    "Chinese",
    "Hindi",
    "Portuguese",
    "Swedish",
    "Russian",
    "Persian",
    "Other",
]

MAINSTREAM_TAG_NEEDLES = (
    "marvel",
    "dc comics",
    "superhero",
    "pixar",
    "blockbuster",
    "franchise",
)

MOODS = [
    {"id": "easy", "label": "Turn your brain off"},
    {"id": "focus", "label": "Pay attention"},
    {"id": "indie", "label": "Indie"},
    {"id": "niche", "label": "Niche"},
    {"id": "foreign", "label": "Foreign"},
    {"id": "tonight", "label": "Tonight"},
    {"id": "date", "label": "Date night"},
    {"id": "family", "label": "Family"},
    {"id": "scary", "label": "Scary"},
    {"id": "comfort", "label": "Comfort"},
    {"id": "thrills", "label": "Thrills"},
]

GENRE_ORDER = [
    "Action",
    "Comedy",
    "Drama",
    "Thriller",
    "Romance",
    "Sci-Fi",
    "Animation",
    "Horror",
    "Adventure",
    "Crime",
    "Fantasy",
    "Mystery",
    "Documentary",
    "Children",
    "War",
    "Musical",
    "Western",
    "Film-Noir",
]

STARTER_MUST_IDS = [
    1, 318, 296, 356, 260, 2571, 79132, 2959, 4993, 58559, 1196, 1198,
    858, 1221, 50, 527, 593, 2028, 7153, 4226, 1136, 608, 47, 2858,
    109487, 44191, 89745, 60069, 68954, 5618, 1704, 1193, 912, 750,
    904, 908, 1203, 1222, 1213, 1089, 111, 924, 541, 1200, 1214, 32,
    4878, 7361, 4973, 2324, 3147, 778, 1258, 1208, 1228, 1247,
]

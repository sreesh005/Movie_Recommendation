export type WatchWindow = {
  genre: string;
  slot: string;
  when: string;
  detail: string;
  hours: number[];
  dows: number[];
  moods: string[];
};

export type Movie = {
  movie_id: number;
  title: string;
  year: number | null;
  genres: string[];
  tags: string[];
  avg_rating: number;
  rating_count: number;
  imdb_id: string | null;
  tmdb_id: number | null;
  poster_url: string | null;
  language: string | null;
  watch: WatchWindow;
};

export type RecMovie = Movie & {
  predicted_rating: number;
  reason: string;
  because_you_liked: { movie_id: number; title: string } | null;
  tonight_fit: boolean;
};

export type GenreRow = { name: string; movies: RecMovie[] };

export type RecommendResponse = {
  hero: RecMovie | null;
  top: RecMovie[];
  tonight: RecMovie[];
  weekend: RecMovie[];
  weeknight: RecMovie[];
  hidden: RecMovie[];
  indie: RecMovie[];
  niche: RecMovie[];
  foreign: RecMovie[];
  because: { title: string; movies: RecMovie[] }[];
  genres: GenreRow[];
  mood: string;
  count_ratings: number;
  personalized: boolean;
};

export type GenreInfo = { id: string; count: number };

export type View =
  | { name: "home" }
  | { name: "survey" }
  | { name: "browse"; genre: string | null }
  | { name: "library" }
  | { name: "movie"; id: number };

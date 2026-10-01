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
  watch: WatchWindow;
};

export type RecMovie = Movie & {
  predicted_rating: number;
  reason: string;
  because_you_liked: { movie_id: number; title: string } | null;
  tonight_fit: boolean;
};

export type RecommendResponse = {
  hero: RecMovie | null;
  top: RecMovie[];
  tonight: RecMovie[];
  hidden: RecMovie[];
  because: { title: string; movies: RecMovie[] }[];
  count_ratings: number;
  personalized: boolean;
};

export type View =
  | { name: "tonight" }
  | { name: "rate" }
  | { name: "foryou" }
  | { name: "movie"; id: number };

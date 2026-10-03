"""Builds the Case Study 3 Word report from the class template."""

from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.shared import Inches

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = Path(r"C:\Users\kkr84\Downloads\DAEN 400 Case Study Report Template Fa26 (Revised) (2).docx")
OUT_DIR = ROOT / "artifacts" / "report"
FIG_DIR = OUT_DIR / "figures"
DEST = ROOT / "Case_Study_3_Later.docx"
DOWNLOADS = Path(r"C:\Users\kkr84\Downloads\Case_Study_3_Later.docx")


def delete_element(el) -> None:
    parent = el.getparent()
    if parent is not None:
        parent.remove(el)


def set_run_text(paragraph, text: str) -> None:
    runs = paragraph.runs
    if not runs:
        paragraph.add_run(text)
        return
    runs[0].text = text
    for run in runs[1:]:
        run.text = ""


def add_page_break(doc: Document) -> None:
    p = doc.add_paragraph()
    p.add_run().add_break(WD_BREAK.PAGE)


def caption(doc: Document, text: str) -> None:
    p = doc.add_paragraph(text, style="Caption")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER


def body(doc: Document, text: str) -> None:
    doc.add_paragraph(text, style="Normal")


def heading(doc: Document, text: str, level: int) -> None:
    doc.add_heading(text, level=level)


def add_picture(doc: Document, path: Path, width: float = 6.3) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(str(path), width=Inches(width))


def add_table(doc: Document, headers: list[str], rows: list[list[str]]) -> None:
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True
    for r, row in enumerate(rows, start=1):
        for c, val in enumerate(row):
            table.rows[r].cells[c].text = val
    doc.add_paragraph()


def make_figures() -> dict[str, Path]:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )

    # fig 1: architecture
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.2)
    ax.axis("off")
    boxes = [
        (0.25, 1.4, 2.2, 1.5, "MovieLens 32M\nratings, tags,\nlinks"),
        (2.85, 1.4, 2.3, 1.5, "LensKit ImplicitMF\n+ genre cosine\n+ log-count pop"),
        (5.55, 1.4, 2.1, 1.5, "FastAPI\nhybrid ranker\nwatch windows"),
        (8.05, 1.4, 1.7, 1.5, "React UI\nLater"),
    ]
    for x, y, w, h, label in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.04,rounding_size=0.12",
                facecolor="#F4EBD8",
                edgecolor="#3A3226",
                linewidth=1.2,
            )
        )
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=9)
    for x0, x1 in [(2.45, 2.85), (5.15, 5.55), (7.65, 8.05)]:
        ax.annotate(
            "",
            xy=(x1, 2.15),
            xytext=(x0, 2.15),
            arrowprops=dict(arrowstyle="->", color="#3A3226", lw=1.4),
        )
    ax.set_title("Serving path for Later")
    fig.tight_layout()
    fig1 = FIG_DIR / "fig1_architecture.png"
    fig.savefig(fig1, dpi=180, bbox_inches="tight")
    plt.close(fig)

    # fig 2: hybrid weights
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    labels = ["0 ratings\n(cold start)", "1–4 ratings", "5+ ratings"]
    knn = [0.0, 0.35, 0.62]
    content = [0.0, 0.40, 0.23]
    pop = [1.0, 0.25, 0.15]
    x = range(len(labels))
    w = 0.25
    ax.bar([i - w for i in x], knn, width=w, label="ImplicitMF (CF)", color="#C9A227")
    ax.bar(list(x), content, width=w, label="Genre cosine", color="#5C6B73")
    ax.bar([i + w for i in x], pop, width=w, label="Log-count popularity", color="#B2553A")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Weight after min–max scaling")
    ax.set_ylim(0, 1.15)
    ax.legend(frameon=False, loc="upper right")
    ax.set_title("Hybrid score weights by number of user ratings")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig2 = FIG_DIR / "fig2_hybrid_weights.png"
    fig.savefig(fig2, dpi=180, bbox_inches="tight")
    plt.close(fig)

    # fig 3: holdout results
    fig, ax = plt.subplots(figsize=(6.8, 3.7))
    metrics = ["Recall@20", "nDCG@20"]
    random_s = [0.00086, 0.00086]
    knn_s = [0.0067, 0.0058]
    live_s = [0.2783, 0.2037]
    x = range(len(metrics))
    w = 0.24
    ax.bar([i - w for i in x], random_s, width=w, label="Uniform random", color="#C5B9A8")
    ax.bar(list(x), knn_s, width=w, label="ItemKNN (predicted rating)", color="#5C6B73")
    ax.bar([i + w for i in x], live_s, width=w, label="Hybrid + ImplicitMF", color="#C9A227")
    ax.set_xticks(list(x))
    ax.set_xticklabels(metrics)
    ax.set_ylabel("Score")
    ax.set_title("Offline ranking on the 120-user holdout")
    ax.legend(frameon=False, fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig3 = FIG_DIR / "fig3_offline_metrics.png"
    fig.savefig(fig3, dpi=180, bbox_inches="tight")
    plt.close(fig)

    return {"arch": fig1, "weights": fig2, "metrics": fig3}


def count_words(doc: Document, start_style: str = "Introduction") -> int:
    started = False
    stop_at = {"References (Optional)", "References", "Appendix A: Documentation of AI Use"}
    words = 0
    for p in doc.paragraphs:
        t = p.text.strip()
        if p.style and p.style.name == "Heading 1" and t.startswith("Introduction"):
            started = True
        if started and p.style and p.style.name == "Heading 1" and t in stop_at:
            break
        if started:
            words += len(t.split())
    return words


def build() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    figs = make_figures()
    shutil.copyfile(TEMPLATE, DEST)
    doc = Document(str(DEST))

    replacements = {
        "Title": "Later: A Custom Movie Recommender for MovieLens 32M",
        "Joe Aggie": "Sreesh Kanala",
        "Date (Month, day, year assignment is due)": "October 1, 2026",
        "Signature *   _________________________": "Signature *   Sreesh Kanala",
        "Google Gemini assisted with revisions to this template.": (
            "Cursor was used to draft report sections, generate figure code, and check grammar. "
            "Training, metrics, and final wording were reviewed by the author."
        ),
        "Submitted to fulfill the requirement for Case Study X": (
            "Submitted to fulfill the requirement for Case Study 3"
        ),
    }
    for para in doc.paragraphs:
        raw = para.text.strip()
        if raw in replacements:
            set_run_text(para, replacements[raw])
        elif raw.startswith("Artificial Intelligence (AI) Acknowledgement:"):
            set_run_text(para, "Artificial Intelligence (AI) Acknowledgement:")

    # remove the template's signing note
    for para in list(doc.paragraphs):
        t = para.text.strip()
        if t.startswith("*You may sign and scan"):
            delete_element(para._element)

    # keep the cover page, drop the template body
    drop = False
    for para in list(doc.paragraphs):
        t = para.text.strip()
        if t.startswith("Explanatory notes are in blue"):
            drop = True
        if drop:
            delete_element(para._element)

    for tbl in list(doc.tables):
        delete_element(tbl._tbl)

    # --- Executive Summary ---
    heading(doc, "Executive Summary", 1)
    body(
        doc,
        "This project was undertaken to solve a familiar evening problem: too many movies, too little "
        "guidance about which one belongs on the screen tonight. A LensKit pipeline was trained on "
        "MovieLens 32M and wrapped in a poster-first web app, Later, that also suggests when to watch. "
        "Three choices shaped the work. First, the catalog was limited to films with at least 20 ratings "
        "and models were fit on 31.7 million of those ratings. Second, collaborative scores were blended "
        "with genre taste and log-count popularity so a user who has only rated a handful of titles still "
        "gets a list. Third, each title received a watch window from genre rules and America/Chicago "
        "rating-hour histograms. Ranking by predicted rating failed: ItemKNN nDCG@20 was 0.0058 on a "
        "120-user holdout. Replacing that objective with implicit matrix factorization raised nDCG@20 "
        "to 0.2037 and recall@20 to 0.2783 — 167 hits in 600 hidden films instead of four. The same "
        "holdout gave ItemKNN an RMSE of 0.861 for star prediction and a logistic like/dislike accuracy "
        "of 70.5%. The live product opens on a hero poster, mood chips, and a library of rated and "
        "rejected titles. Watch windows should still be read as rating-time proxies, not viewing times.",
    )
    add_page_break(doc)

    heading(doc, "Table of Contents", 1)
    body(
        doc,
        "Right-click this heading in Microsoft Word, then use References → Table of Contents to insert "
        "or update an automatic table. Numbered Heading 1 and Heading 2 styles are used throughout.",
    )
    for line in [
        "Executive Summary",
        "1. Introduction",
        "2. Methods",
        "3. Results",
        "4. Conclusions",
        "5. Limitations",
        "6. Recommendations",
        "7. References",
        "Appendix A: Documentation of AI Use",
        "Appendix B: Supporting Data",
    ]:
        doc.add_paragraph(line, style="List Paragraph")

    heading(doc, "List of Figures", 1)
    for line in [
        "Figure 1. Serving path from MovieLens 32M to the Later interface.",
        "Figure 2. Hybrid score weights by number of user ratings.",
        "Figure 3. Offline recall@20 and nDCG@20 for ItemKNN versus the live hybrid.",
    ]:
        doc.add_paragraph(line, style="List Paragraph")

    heading(doc, "List of Tables", 1)
    for line in [
        "Table 1. Training catalog after the 20-rating movie floor.",
        "Table 2. Modeling options considered and the choice made.",
        "Table 3. Offline ranking on 120 held-out users.",
        "Table 4. Star-prediction RMSE and like/dislike accuracy.",
        "Table 5. Example titles returned by the two energy moods.",
        "Table 6. Example watch windows by primary genre (Appendix B).",
    ]:
        doc.add_paragraph(line, style="List Paragraph")
    add_page_break(doc)

    # --- Introduction ---
    heading(doc, "Introduction", 1)
    body(
        doc,
        "A person sits down to watch something. The catalog is the problem GroupLens has studied "
        "since 1997: tens of thousands of titles, a few films already loved, and no obvious next "
        "click (Harper & Konstan, 2015). MovieLens 32M makes that pile concrete — 32,000,204 ratings "
        "and 2,000,072 tags on 87,585 movies. The assignment was to build a custom recommender with "
        "LensKit (Ekstrand, 2020), make the interface feel like a streaming home page, cite products "
        "people already know, and add one extra beat: when the recommended film should be watched.",
    )
    heading(doc, "Problem identification", 2)
    body(
        doc,
        "The hard part is finishing the decision. Name eight films and the unseen remainder is still "
        "enormous. A high predicted rating on 12 Angry Men is the wrong answer if the room wants "
        "something that can be half-watched. Netflix, Letterboxd, and Amazon’s item-to-item CF "
        "(Linden et al., 2003; Sarwar et al., 2001) each solve a piece of that problem. None of them, "
        "used as-is, trains on this MovieLens dump or prints a watch window on the poster. Later was "
        "built to close that gap.",
    )
    heading(doc, "Related systems", 2)
    body(
        doc,
        "Netflix, Letterboxd, MovieLens, and Amazon’s item-to-item CF (Linden et al., 2003) are the "
        "references for rows, starring, research ratings, and neighbor lookup.",
    )

    # --- Methods ---
    heading(doc, "Methods", 1)
    heading(doc, "Methods considered", 2)
    body(
        doc,
        "The first fork was the interface. Streamlit, Flask, and React were all on the table. Streamlit "
        "is the example in the assignment brief and would have been the fastest way to a demo. It was "
        "set aside because an “intuitive” recommender has to feel like browsing posters, not filling "
        "out a form. React with a FastAPI backend kept the model in Python and let the home page "
        "behave like a streaming app: lists stay on screen, half-stars are tappable, and a back "
        "button returns to the same row.",
    )
    body(
        doc,
        "The second fork was the model. The in-class plan named matrix factorization, item–item "
        "k-nearest neighbors, graph random walks, and a two-tower neural ranker. A two-tower network "
        "was too heavy for a single-machine pass over 32 million ratings on an educational deadline. "
        "Graph walks added little on explicit five-star data. LensKit’s "
        "ItemKNNScorer was trained first because it is native to the assigned library and because "
        "neighbor lookup can be shown as “because you liked X” (Linden et al., 2003; Sarwar et al., 2001). "
        "That predicted-rating ranker collapsed on top-N. Implicit matrix factorization (Hu et al., 2008; "
        "Koren et al., 2009) was then trained on liked ratings and became the collaborative term in "
        "the live hybrid. ItemKNN was kept as the star predictor for RMSE. Table 2 records the choice.",
    )
    heading(doc, "Data preparation", 2)
    body(
        doc,
        "The 32 million-row file was scanned in full. Movies with fewer than 20 ratings were dropped, "
        "which cut 87,585 titles down to 23,350 and still kept 31,722,609 ratings — about 99 percent "
        "of the file. Every user with at least 20 ratings on that catalog stayed in (200,763 people). "
        "Tags were reduced to the four most common per movie. Poster paths came from The Movie "
        "Database via links.csv. The 20-rating floor is the usual GroupLens cold-item cutoff: below "
        "it, item–item CF has almost no neighborhood to stand on.",
    )
    heading(doc, "Hybrid ranking", 2)
    body(
        doc,
        "For a user with rating vector r, LensKit ImplicitMF returns ranking scores on items the "
        "user has not rated, using liked titles (rating ≥ 4) as implicit feedback (64 factors, 10 "
        "epochs). Those scores are multiplied by log(1 + rating count) so obscure high-mean films do "
        "not dominate. A content score is the cosine between the user’s genre profile, with ratings "
        "centered at 3.0, and each candidate’s genre vector. Popularity is the same log-count signal. "
        "After min–max normalization, the production score is",
    )
    eq = doc.add_paragraph()
    eq.alignment = WD_ALIGN_PARAGRAPH.CENTER
    eq.add_run(
        "s(i) = w_cf cf(i) + w_c content(i) + w_p pop(i) + 0.08·1_hour(i) + 0.05·1_dow(i) − 0.22·sim(i, reject)"
    ).italic = True
    eq_cap = doc.add_paragraph()
    eq_cap.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    eq_cap.add_run("(1)")
    body(
        doc,
        "Equation 1 is what the API actually ranks. With no ratings, popularity carries the list. With "
        "one to four ratings, genre taste and collaborative scores share the load. After five ratings, "
        "collaborative filtering takes the majority vote (0.62 / 0.23 / 0.15). Titles marked not "
        "interested are removed and also pull down similar genre vectors. Mood chips are exclusive: "
        "Parasite cannot sit in both Comfort and Date night. A second pair of chips, laid-back versus "
        "pay-attention, cuts on cognitive load rather than genre.",
    )
    heading(doc, "Watch-time windows", 2)
    body(
        doc,
        "Each primary genre has a heuristic slot (horror after 8 p.m. Friday, drama on Sunday "
        "evening). Peak hour and weekday came from rating timestamps in America/Chicago and are "
        "labeled as a proxy, not a viewing diary. Appendix B lists examples.",
    )
    heading(doc, "Evaluation protocol", 2)
    body(
        doc,
        "Five randomly held-out ratings were peeled off 120 users (seed 42). Ranking used recall@20 "
        "and nDCG@20 against those 600 titles; a uniform draw of 20 from 23,350 has recall@20 = 0.00086. "
        "Star error used LensKit’s ItemKNN rating predictor on the same 600 ratings (RMSE and MAE). "
        "Like/dislike accuracy used a logistic classifier — rating ≥ 4 as the positive class — trained "
        "on those users’ remaining history (6,893 rows) and tested on the holdout. Mood chips and "
        "watch-hour boosts are live-only and are not inside the holdout numbers.",
    )

    # --- Results ---
    heading(doc, "Results", 1)
    heading(doc, "What the 32M file became", 2)
    body(
        doc,
        "Table 1 is the catalog after the long tail was cut. The original dump has 87,585 movies; "
        "23,350 of them had enough ratings to train. That filter dropped almost two-thirds of titles "
        "and almost none of the signal: 31.72 million of 32.00 million ratings survived. Mean rating "
        "on those rows was 3.545. TMDB returned posters for 23,027 of the 23,350 films, so the home "
        "page is almost entirely artwork rather than title cards. Figure 1 is the path those numbers "
        "travel at request time: parquet and pickled LensKit pipelines into FastAPI, then into React.",
    )
    add_table(
        doc,
        ["Quantity", "Value"],
        [
            ["Source dataset", "MovieLens 32M (GroupLens, 2023)"],
            ["Movies in the raw dump", "87,585"],
            ["Movies with ≥ 20 ratings (trained)", "23,350"],
            ["Ratings in the raw dump", "32,000,204"],
            ["Training ratings kept", "31,722,609 (99.1%)"],
            ["Training users (≥ 20 ratings)", "200,763"],
            ["Global mean rating", "3.545"],
            ["TMDB posters cached", "23,027 of 23,350"],
            ["Timezone for watch histograms", "America/Chicago"],
        ],
    )
    caption(doc, "Table 1. Training catalog after the 20-rating movie floor.")
    add_picture(doc, figs["arch"])
    caption(doc, "Figure 1. Serving path from MovieLens 32M to the Later interface.")

    heading(doc, "The fork that was taken", 2)
    body(
        doc,
        "Table 2 is the paper trail of that choice. Streamlit stayed on the slide and never shipped. "
        "The two-tower network stayed in the plan. What shipped was implicit matrix factorization plus "
        "the genre and log-count overlay, with ItemKNN kept as a star predictor, served by FastAPI "
        "into a React home page.",
    )
    add_table(
        doc,
        ["Option", "Role in the plan", "Outcome"],
        [
            ["Streamlit UI", "Assignment example; fastest prototype", "Not used"],
            ["React + FastAPI", "Poster-first product UI", "Adopted"],
            ["Item–item KNN (LensKit)", "Amazon-style CF; star predictor", "Baseline / RMSE model"],
            ["Implicit MF / ALS", "Ranking CF on liked ratings", "Live collaborative term"],
            ["Two-tower network", "Neural retrieval", "Not trained"],
            ["Hybrid genre + log-count", "Cold-start and popularity overlay", "Adopted"],
            ["LLM mood chatbot", "Semantic mood input", "Not built"],
        ],
    )
    caption(doc, "Table 2. Modeling options considered and the choice made.")
    body(
        doc,
        "Figure 2 shows what that hybrid does as a person rates more films. At zero ratings the list "
        "is log-count popularity. After the first few stars, genre cosine takes 40 percent of the vote and "
        "collaborative scores 35 percent. Once five ratings are in, collaborative filtering is 62 percent of "
        "the score. That is the same threshold the survey uses: Home does not personalize until "
        "eight films are rated, so the live app always sits in the rightmost bar of Figure 2.",
    )
    add_picture(doc, figs["weights"], 6.0)
    caption(doc, "Figure 2. Hybrid score weights by number of user ratings.")

    heading(doc, "Holdout ranking: predicted rating was the wrong objective", 2)
    body(
        doc,
        "Five ratings were peeled off 120 users and each ranker was asked for 20 titles. That is 600 "
        "hidden films. ItemKNN, ranking by predicted rating, put about four of them in those top-20 "
        "lists (recall@20 = 0.0067, nDCG@20 = 0.0058). The lists were cinephile high-mean titles, not "
        "the popular films people actually rate. Count popularity alone already reached nDCG@20 of "
        "0.1134. ImplicitMF on liked ratings reached 0.1558. The live blend — ImplicitMF × log-count, "
        "genre cosine, and log-count popularity — reached recall@20 of 0.2783 and nDCG@20 of 0.2037: "
        "167 hits in 600, about 35 times the ItemKNN number and far above a uniform draw of 20 from "
        "23,350 (recall@20 = 0.00086). Table 3 and Figure 3 put those figures side by side. Mood "
        "filters and watch-hour boosts are not in that holdout.",
    )
    add_table(
        doc,
        ["Ranker", "Hits / 600", "Recall@20", "nDCG@20"],
        [
            ["Uniform random", "~0.5", "0.00086", "~0.00086"],
            ["ItemKNN (predicted rating)", "4", "0.0067", "0.0058"],
            ["Count popularity", "89", "0.1483", "0.1134"],
            ["ImplicitMF (liked ratings)", "136", "0.2267", "0.1558"],
            ["Hybrid + ImplicitMF (live)", "167", "0.2783", "0.2037"],
        ],
    )
    caption(doc, "Table 3. Offline ranking on 120 held-out users.")
    add_picture(doc, figs["metrics"], 5.8)
    caption(doc, "Figure 3. Offline recall@20 and nDCG@20 for ItemKNN versus the live hybrid.")

    heading(doc, "Star error and like/dislike accuracy", 2)
    body(
        doc,
        "ImplicitMF does not output one-to-five stars, so RMSE is not a property of the live list. "
        "Star error was scored with the ItemKNN rating predictor on the same 600 hidden ratings. "
        "RMSE was 0.861 and MAE was 0.641, better than a user-mean baseline (0.987). A logistic "
        "classifier trained to predict ratings of 4 or higher from user mean, item Bayesian average, "
        "log-count, and genre cosine (Pedregosa et al., 2011) reached 70.5% accuracy on the holdout, against a 52.7% "
        "majority-class baseline (316 of 600 hidden ratings were ≥ 4). Precision was 0.706; recall "
        "was 0.753. Thresholding the ItemKNN star prediction at 4.0 was almost as accurate (70.3%). "
        "Table 4 is the comparison.",
    )
    add_table(
        doc,
        ["Model", "RMSE", "MAE", "Like accuracy"],
        [
            ["ItemKNN rating predictor", "0.861", "0.641", "70.3%"],
            ["User mean", "0.987", "0.750", "58.8%"],
            ["Item Bayesian average", "1.003", "0.776", "55.0%"],
            ["Global mean", "1.112", "0.880", "47.3%"],
            ["Logistic like/dislike (≥ 4★)", "—", "—", "70.5%"],
        ],
    )
    caption(doc, "Table 4. Star-prediction RMSE and like/dislike accuracy.")

    heading(doc, "What the live home page actually served", 2)
    body(
        doc,
        "After eight survey ratings, Home opens on a hero poster with a predicted rating, a one-line "
        "reason, and a watch pill. Exclusive mood rules stopped Parasite from sitting in both Comfort "
        "and Date night. Indie, niche, and foreign sit as discovery lanes, with foreign filterable by "
        "inferred language.",
    )
    body(
        doc,
        "A second pair of chips asks laid-back versus pay attention. Table 5 is what that filter "
        "returned after a survey that included Pulp Fiction, Shawshank, Forrest Gump, The Godfather, "
        "Goodfellas, Whiplash, and Parasite. An earlier easy filter had also let The Dark Knight "
        "through on a superhero tag; those titles were then excluded so laid-back meant easy company.",
    )
    add_table(
        doc,
        ["Chip", "Hero", "Example row"],
        [
            [
                "Turn your brain off",
                "Spirited Away (2001)",
                "The Intouchables; Howl’s Moving Castle; Amélie; Up; Fantastic Mr. Fox",
            ],
            [
                "Pay attention",
                "12 Angry Men (1957)",
                "Whiplash; Schindler’s List; The Usual Suspects; The Big Short; Sicario",
            ],
        ],
    )
    caption(doc, "Table 5. Example titles returned by the two energy moods.")
    body(
        doc,
        "Watch pills still read “Friday night” for horror and “Sunday evening” for drama, but the "
        "histogram peak for nearly every genre landed on Sunday around 3 p.m. Chicago time. Drama "
        "accounts for 13.9 million of those rating events; comedy 11.1 million; action 9.6 million "
        "(Appendix B). The interface prints the caveat: rating time is a proxy, not a viewing diary.",
    )
    body(
        doc,
        "Tapping Not interested on a hero removed it from Home and filed it in Library with rated "
        "titles. Half-stars of 3½ and 4½ were accepted in the same control. Foreign languages opened "
        "as a horizontal slider instead of a wrapped cloud of chips.",
    )

    # --- Conclusions ---
    heading(doc, "Conclusions", 1)
    heading(doc, "The objective had to change", 2)
    body(
        doc,
        "Item–item CF still predicts stars on this catalog (RMSE 0.861). It is the wrong objective "
        "for a home-page list. Ranking by predicted rating produced nDCG@20 of 0.0058; the live "
        "ImplicitMF hybrid produced 0.2037. The hybrid overlay still matters for a simpler reason: "
        "eight survey ratings are not a dense history. Content and log-count popularity carry the "
        "user until Figure 2’s rightmost bar is in force.",
    )
    heading(doc, "The app’s best findings were qualitative", 2)
    body(
        doc,
        "The live home page did two things ranking nDCG cannot see. Exclusive moods stopped "
        "Parasite from appearing as both comfort and date night. The energy chips split the catalog "
        "in a way a person can feel: Ghibli and Up on one side, 12 Angry Men and Schindler’s List on "
        "the other. Watch windows, meanwhile, mostly discovered when people rate. Sunday-afternoon "
        "peaks across horror, drama, and comedy are consistent with logging catch-up, not with a "
        "nation watching slashers at 3 p.m. The interface already says so.",
    )

    # --- Limitations ---
    heading(doc, "Limitations", 1)
    heading(doc, "Holdout size and unmeasured UI terms", 2)
    body(
        doc,
        "One hundred twenty users is a thin slice of 200,763. Mood filters and watch-hour boosts are "
        "still outside Table 3. The logistic classifier was trained on the same users’ remaining "
        "history, so 70.5% accuracy is not a claim about a new population. No paired significance "
        "test against a full SVD bake-off was run.",
    )
    heading(doc, "Timestamps and language are proxies", 2)
    body(
        doc,
        "MovieLens timestamps record when a rating was saved, not when a film was watched. Foreign "
        "language is inferred from tags and titles, not TMDB original-language metadata. There was "
        "no online A/B test. The not-interested penalty is a coarse cosine against a reject genre "
        "vector and will over-penalize other films that share a skipped title’s genre.",
    )

    # --- Recommendations ---
    heading(doc, "Recommendations", 1)
    heading(doc, "Score moods on a larger sample; leave the chips alone", 2)
    body(
        doc,
        "The holdout should be repeated on more than 120 users, with a paired test of ImplicitMF "
        "against a biased SVD. Mood chips will not move that number until they are part of the "
        "protocol. The React interface already meets the “intuitive UI” requirement.",
    )
    heading(doc, "Treat watch windows as a UI extra until play events exist", 2)
    body(
        doc,
        "Watch windows should not be deployed as if they were viewing times. Play-start events would "
        "replace the rating-hour histograms and would be the highest-leverage upgrade to the “when "
        "to watch” extra. Original language should come from TMDB rather than tags.",
    )

    heading(doc, "References", 1)
    refs = [
        "Ekstrand, M. D. (2020). LensKit for Python: Next-generation software for recommender systems experiments. In Proceedings of the 29th ACM International Conference on Information and Knowledge Management (pp. 2999–3006). https://doi.org/10.1145/3340531.3412778",
        "GroupLens Research. (2023). MovieLens 32M [Data set]. University of Minnesota. https://grouplens.org/datasets/movielens/",
        "Harper, F. M., & Konstan, J. A. (2015). The MovieLens datasets: History and context. ACM Transactions on Interactive Intelligent Systems, 5(4), 1–19. https://doi.org/10.1145/2827872",
        "Hu, Y., Koren, Y., & Volinsky, C. (2008). Collaborative filtering for implicit feedback datasets. In 2008 Eighth IEEE International Conference on Data Mining (pp. 263–272). https://doi.org/10.1109/ICDM.2008.22",
        "Koren, Y., Bell, R., & Volinsky, C. (2009). Matrix factorization techniques for recommender systems. Computer, 42(8), 30–37. https://doi.org/10.1109/MC.2009.263",
        "Letterboxd. (n.d.). Letterboxd. https://letterboxd.com/",
        "Linden, G., Smith, B., & York, J. (2003). Amazon.com recommendations: Item-to-item collaborative filtering. IEEE Internet Computing, 7(1), 76–80. https://doi.org/10.1109/MIC.2003.1167344",
        "Netflix. (n.d.). Netflix. https://www.netflix.com/",
        "Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., Cournapeau, D., Brucher, M., Perrot, M., & Duchesnay, É. (2011). Scikit-learn: Machine learning in Python. Journal of Machine Learning Research, 12, 2825–2830.",
        "Sarwar, B., Karypis, G., Konstan, J., & Riedl, J. (2001). Item-based collaborative filtering recommendation algorithms. In Proceedings of the 10th International Conference on World Wide Web (pp. 285–295). https://doi.org/10.1145/371920.372071",
    ]
    for ref in refs:
        p = doc.add_paragraph(ref, style="Normal")
        p.paragraph_format.left_indent = Inches(0.5)
        p.paragraph_format.first_line_indent = Inches(-0.5)

    heading(doc, "Appendix A: Documentation of AI Use", 1)
    body(
        doc,
        "Cursor (Grok) was used as a coding and writing assistant for the recommender and for this report.",
    )
    heading(doc, "Prompts and outputs", 2)
    body(
        doc,
        "Prompt 1: “Rewrite the Case Study 3 report so it flows like a story and expand the Results "
        "section with catalog, holdout, mood, and watch-window detail.” Summary: a revised draft with "
        "a narrative introduction, a thicker Results section (including Table 5’s energy-mood "
        "examples), and the same required headings. Numbers were checked against artifacts/metrics.json.",
    )
    body(
        doc,
        "Prompt 2: “Create figures for architecture, hybrid weights, and holdout metrics.” Summary: "
        "Python (matplotlib) code that produced Figures 1–3. Axis labels and colors were adjusted "
        "before insertion.",
    )
    body(
        doc,
        "Prompt 3: “Put RMSE 0.861 and 70.5% like/dislike accuracy in the report with the new nDCG.” "
        "Summary: Table 3 became a ranking comparison; Table 4 added star error and accuracy. "
        "Numbers were checked against artifacts/metrics.json.",
    )
    heading(doc, "Comparison with the in-class plan", 2)
    body(
        doc,
        "The in-class plan stated that Streamlit was the likely interface, that SVD, k-NN, graph "
        "walks, and a two-tower network would be compared, that a hybrid might be used, and that an "
        "LLM chatbot might judge mood. It expected genre preference and watch-time if time data "
        "existed, and it warned that exact title prediction would be hard because not every comedy "
        "shares the same humor.",
    )
    body(
        doc,
        "The built system departed from that plan in three ways. First, Streamlit was replaced by "
        "React and FastAPI so the UI could be poster-first. Second, graph walks and two-tower models "
        "were not trained; item–item KNN was fit first, then implicit matrix factorization became the "
        "live collaborative term after predicted-rating ranking failed on the holdout. Third, the LLM "
        "chatbot was not built; mood is handled with exclusive chips, including laid-back versus "
        "pay-attention. The plan’s warning about exact title prediction was the first result: ItemKNN "
        "recall@20 of 0.0067. The live hybrid recovered the list (recall@20 0.2783, nDCG@20 0.2037). "
        "Watch-time was implemented, but from rating timestamps rather than true viewing logs.",
    )

    heading(doc, "Appendix B: Supporting Data", 1)
    body(
        doc,
        "Table 6 lists a subset of the genre watch windows stored in artifacts/watch_windows.json. "
        "Peak hour and weekday are the modes of rating timestamps in America/Chicago. Observation "
        "counts are rating events, not plays.",
    )
    add_table(
        doc,
        ["Genre", "Slot", "When", "Peak (histogram)", "Rating events"],
        [
            ["Horror", "Friday night", "After 8pm", "Sunday ~3pm", "2,462,938"],
            ["Children", "Weekend afternoon", "Saturday 1–4pm", "Sunday ~3pm", "2,717,791"],
            ["Romance", "Saturday evening", "Date night around 8pm", "Sunday ~3pm", "5,492,692"],
            ["Comedy", "Weeknight", "Unwind after 7pm", "Sunday ~3pm", "11,135,697"],
            ["Drama", "Sunday evening", "When you can pay attention", "Sunday ~3pm", "13,865,970"],
            ["Action", "Saturday night", "Prime time 8pm", "Sunday ~3pm", "9,635,828"],
            ["Documentary", "Sunday morning", "Coffee and a documentary", "Sunday ~3pm", "396,222"],
        ],
    )
    caption(doc, "Table 6. Example watch windows by primary genre (Appendix B).")

    doc.save(str(DEST))
    words = count_words(doc)
    print(f"Wrote {DEST}")
    print(f"Body word count (Introduction through Recommendations): {words}")
    for dest in (
        DOWNLOADS,
        Path(r"C:\Users\kkr84\Downloads\Case_Study_3_Later_v2.docx"),
        Path(r"C:\Users\kkr84\Downloads\Case_Study_3_Later_v3.docx"),
    ):
        try:
            shutil.copyfile(DEST, dest)
            print(f"Copied {dest}")
        except PermissionError:
            print(f"Locked, skipped {dest}")


if __name__ == "__main__":
    build()

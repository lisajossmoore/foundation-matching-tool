from pathlib import Path
from typing import List, Tuple, Dict
import pandas as pd
import typer
from rich import print
from rapidfuzz import fuzz, process

app = typer.Typer(add_completion=False)

def _split_keywords(s: str, sep: str) -> List[str]:
    if not isinstance(s, str) or not s.strip():
        return []
    # Normalize, split, strip, deduplicate
    parts = [p.strip().lower() for p in s.replace("\n", " ").split(sep)]
    return sorted(list({p for p in parts if p}))

def _pairwise_best_scores(fac_kw: List[str], fund_kw: List[str]) -> Tuple[float, List[Tuple[str, str, int]]]:
    """
    Returns (overall_score, matched_pairs) where overall_score is max fuzzy score (0-100)
    and matched_pairs lists (faculty_kw, foundation_kw, score) for top matches.
    """
    matches: List[Tuple[str, str, int]] = []
    best_overall = 0
    for fkw in fac_kw:
        # Find best foundation keyword for this faculty keyword
        best = None
        best_score = -1
        for nkw in fund_kw:
            # Combine exact-ish and fuzzy: partial_ratio catches stems/phrases reasonably well
            score = max(
                fuzz.partial_ratio(fkw, nkw),
                fuzz.token_set_ratio(fkw, nkw),
            )
            if score > best_score:
                best_score = score
                best = nkw
        if best is not None:
            matches.append((fkw, best, int(best_score)))
            if best_score > best_overall:
                best_overall = int(best_score)
    # Sort matched pairs by score desc, then fkw
    matches.sort(key=lambda x: (-x[2], x[0]))
    return best_overall, matches

@app.command()
def match(
    foundations: Path = typer.Option(..., "--foundations", "-f", help="Path to foundations Excel (xlsx)"),
    faculty: Path = typer.Option(..., "--faculty", "-p", help="Path to faculty Excel (xlsx)"),
    out: Path = typer.Option(Path("outputs/matches.xlsx"), "--out", "-o", help="Output Excel path"),
    score_threshold: int = typer.Option(60, help="Only include matches with score >= this (0-100)"),
    top_n_per_faculty: int = typer.Option(20, help="Max foundations to keep per faculty after filtering")
):
    """
    Read two Excel files, do keyword + fuzzy matching, and write ranked matches to Excel.
    """
    print(f"[bold]Reading[/bold] foundations from: {foundations}")
    print(f"[bold]Reading[/bold] faculty from: {faculty}")

    # --- Load sheets
    fnd = pd.read_excel(foundations)
    fac = pd.read_excel(faculty)

    # --- Expected columns (case-insensitive match)
    foundation_cols = {
        "foundation name": "Foundation Name",
        "area of funding": "Area of Funding",
        "average grant": "Average Grant",
        "career stage targeted": "Career Stage Targeted",
        "deadlines/restrictions": "Deadlines/Restrictions",
        "institution preference": "Institution Preference",
        "website": "Website",
    }
    faculty_cols = {
        "name": "Name",
        "degree": "Degree",
        "rank": "Rank",
        "division": "Division",
        "career stage": "Career Stage",
        "keywords": "Keywords",
    }

    def _normalize_columns(df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
        lower_map = {c.lower().strip(): c for c in df.columns}
        out_cols = {}
        for required_lower, std_name in mapping.items():
            if required_lower in lower_map:
                out_cols[lower_map[required_lower]] = std_name
            else:
                raise ValueError(f"Missing required column in Excel: '{mapping[required_lower]}'")
        return df.rename(columns=out_cols)

    fnd = _normalize_columns(fnd, foundation_cols)
    fac = _normalize_columns(fac, faculty_cols)

    # --- Pre-split keywords
    # Foundations: Area of Funding uses comma-separated keywords
    fnd["__kw"] = fnd["Area of Funding"].fillna("").astype(str).map(lambda s: _split_keywords(s, sep=","))

    # Faculty: Keywords uses semicolon-separated keywords
    fac["__kw"] = fac["Keywords"].fillna("").astype(str).map(lambda s: _split_keywords(s, sep=";"))

    rows = []
    for _, fac_row in fac.iterrows():
        fac_name = str(fac_row["Name"])
        fac_div = str(fac_row["Division"])
        fac_rank = str(fac_row["Rank"])
        fac_stage = str(fac_row["Career Stage"])
        fac_kws = fac_row["__kw"]

        for _, fnd_row in fnd.iterrows():
            fund_name = str(fnd_row["Foundation Name"])
            fund_kws = fnd_row["__kw"]

            score, pairs = _pairwise_best_scores(fac_kws, fund_kws)

            if score >= score_threshold and pairs:
                why = "; ".join([f"{a} ~ {b} ({s})" for a, b, s in pairs[:5]])  # show top 5 reasons
                match_count = sum(1 for _, _, s in pairs if s >= score_threshold)
                rows.append({
                    "Faculty": fac_name,
                    "Rank": fac_rank,
                    "Division": fac_div,
                    "Career Stage": fac_stage,
                    "Top Keywords": "; ".join(fac_kws[:10]),
                    "Foundation": fund_name,
                    "Match Score (0-100)": score,
                    "Matched Keyword Count": match_count,
                    "Why Matched (top)": why,
                    "Average Grant": fnd_row["Average Grant"],
                    "Career Stage Targeted": fnd_row["Career Stage Targeted"],
                    "Deadlines/Restrictions": fnd_row["Deadlines/Restrictions"],
                    "Institution Preference": fnd_row["Institution Preference"],
                    "Website": fnd_row["Website"],
                })

    if not rows:
        print("[yellow]No matches found above the threshold. Try lowering --score-threshold.[/yellow]")
        return

    out_df = pd.DataFrame(rows).sort_values(
        by=["Faculty", "Match Score (0-100)", "Matched Keyword Count"],
        ascending=[True, False, False]
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_excel(out, index=False)
    print(f"[bold green]Wrote matches:[/bold green] {out}  (rows: {len(out_df)})")

if __name__ == "__main__":
    app()

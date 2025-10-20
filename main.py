from pathlib import Path
from typing import List, Tuple, Dict, Optional
import re
import pandas as pd
import typer
from rich import print
from rapidfuzz import fuzz

app = typer.Typer(add_completion=False)

def _norm(s: str) -> str:
    """Normalize a header string for matching."""
    s = s.lower()
    s = re.sub(r"[\s_/|-]+", " ", s)         # collapse separators
    s = re.sub(r"[^a-z0-9 ]+", "", s)        # remove punctuation
    return " ".join(s.split())

def _split_keywords(s: str, sep: str) -> List[str]:
    if not isinstance(s, str) or not s.strip():
        return []
    parts = [p.strip().lower() for p in s.replace("\n", " ").split(sep)]
    return sorted(list({p for p in parts if p}))

def _pairwise_best_scores(fac_kw: List[str], fund_kw: List[str]) -> Tuple[float, List[Tuple[str, str, int]]]:
    matches: List[Tuple[str, str, int]] = []
    best_overall = 0
    for fkw in fac_kw:
        best = None
        best_score = -1
        for nkw in fund_kw:
            score = max(
                fuzz.partial_ratio(fkw, nkw),
                fuzz.token_set_ratio(fkw, nkw),
            )
            if score > best_score:
                best_score = score
                best = nkw
        if best is not None:
            score_i = int(best_score)
            matches.append((fkw, best, score_i))
            if score_i > best_overall:
                best_overall = score_i
    matches.sort(key=lambda x: (-x[2], x[0]))
    return best_overall, matches

def _map_columns(df: pd.DataFrame, required: Dict[str, List[str]]) -> Dict[str, str]:
    """
    Map from dataframe's actual column names -> standardized names using
    alias lists and fuzzy matching. Returns dict of {actual_col: std_name}.
    Raises ValueError if some required std_name cannot be mapped.
    """
    # Precompute normalized headers
    actual_cols = list(df.columns)
    norm_actual = {_norm(c): c for c in actual_cols}

    mapping: Dict[str, str] = {}  # actual_col -> std_name
    debug_rows = []               # for printing what we detected

    for std_name, aliases in required.items():
        # Build a candidate list with fuzzy scores
        best_col: Optional[str] = None
        best_score = -1

        # Try exact/contains on normalized first
        alias_norms = [_norm(a) for a in aliases]
        for na, ac in norm_actual.items():
            # If any alias is fully contained in the normalized actual header, take it
            if any(an in na for an in alias_norms):
                # prefer the longest alias match
                score = max(len(an) for an in alias_norms if an in na)
                if score > best_score:
                    best_score = score
                    best_col = ac

        # If not found, fall back to fuzzy (token_set_ratio) vs best alias
        if best_col is None:
            for ac in actual_cols:
                na = _norm(ac)
                score = max(fuzz.token_set_ratio(na, an) for an in alias_norms)
                if score > best_score:
                    best_score = score
                    best_col = ac

        # Threshold: if even fuzzy is very low (<40), consider it unreliable
        if best_col is None or best_score < 40:
            raise ValueError(f"Missing required column in Excel: '{std_name}'")
        mapping[best_col] = std_name
        debug_rows.append((std_name, best_col, best_score))

    # Pretty print detected mapping
    print("[cyan]Detected column mapping:[/cyan]")
    for std_name, ac, score in sorted(debug_rows, key=lambda x: x[0]):
        print(f"  [bold]{std_name}[/bold]  <-  '{ac}'  (score {score})")
    return mapping

@app.command()
def main(
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

    fnd = pd.read_excel(foundations)
    fac = pd.read_excel(faculty)

    # Define flexible aliases for headers (common human variants)
    foundation_required = {
        "Foundation Name": [
            "foundation name", "funder", "funder name", "name"
        ],
        "Area of Funding": [
            "area of funding", "funding area", "focus areas", "research areas",
            "keywords", "keywords comma separated", "area of funding with keywords",
            "areas", "topics"
        ],
        "Average Grant": [
            "average grant", "average award", "typical award", "award size",
            "grant amount", "amount (high/medium/low)", "funding level"
        ],
        "Career Stage Targeted": [
            "career stage targeted", "career stage", "targeted career stage",
            "eligibility career stage", "stage"
        ],
        "Deadlines/Restrictions": [
            "deadlines/restrictions", "deadlines and restrictions",
            "deadlines", "restrictions", "notes"
        ],
        "Institution Preference": [
            "institution preference", "institution specific preferences",
            "institution-specific preferences", "country", "region",
            "us only", "us", "eligibility location"
        ],
        "Website": [
            "website", "url", "link", "homepage"
        ],
    }
    faculty_required = {
        "Name": ["name", "faculty", "faculty name"],
        "Degree": ["degree", "degrees", "credentials"],
        "Rank": ["rank", "title (rank)", "academic rank", "assistant/associate/full"],
        "Division": ["division", "dept division", "unit"],
        "Career Stage": ["career stage", "stage", "early/mid/late", "career level"],
        "Keywords": ["keywords", "research keywords", "topics", "interests", "keywords semicolon separated"],
    }

    # Map and rename columns according to best matches
    fnd_map = _map_columns(fnd, foundation_required)
    fac_map = _map_columns(fac, faculty_required)
    fnd = fnd.rename(columns=fnd_map)
    fac = fac.rename(columns=fac_map)

    # Pre-split keywords
    fnd["__kw"] = fnd["Area of Funding"].fillna("").astype(str).map(lambda s: _split_keywords(s, sep=","))
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
                why = "; ".join([f"{a} ~ {b} ({s})" for a, b, s in pairs[:5]])
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
                    "Average Grant": fnd_row.get("Average Grant", ""),
                    "Career Stage Targeted": fnd_row.get("Career Stage Targeted", ""),
                    "Deadlines/Restrictions": fnd_row.get("Deadlines/Restrictions", ""),
                    "Institution Preference": fnd_row.get("Institution Preference", ""),
                    "Website": fnd_row.get("Website", ""),
                })

    if not rows:
        print("[yellow]No matches found above the threshold. Try lowering --score-threshold or check keywords.[/yellow]")
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

from pathlib import Path
from typing import List, Tuple, Dict, Optional
import re
import pandas as pd
import typer
from rich import print
from rapidfuzz import fuzz

app = typer.Typer(add_completion=False)

def _norm(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.strip().lower()
    s = s.replace("\u00A0", " ")  # NBSP -> space
    s = re.sub(r"[\s_/|,-]+", " ", s)  # unify separators
    s = re.sub(r"[^a-z0-9 ]+", "", s)  # drop punctuation
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

def _map_columns_best(df: pd.DataFrame, required_aliases: Dict[str, List[str]]) -> Dict[str, str]:
    """
    For each required standard name, choose the actual column with the best fuzzy score
    against any alias. Always choose *something* (best available), then report mapping.
    """
    actual_cols = list(df.columns)
    norm_actual = {_norm(c): c for c in actual_cols}

    mapping: Dict[str, str] = {}
    debug = []

    for std, aliases in required_aliases.items():
        best_col = None
        best_score = -1
        for ac in actual_cols:
            na = _norm(ac)
            # Best score vs any alias
            score = max(fuzz.token_set_ratio(na, _norm(alias)) for alias in aliases)
            if score > best_score:
                best_score = score
                best_col = ac
        # Fallback: if nothing reasonable, pick the first column
        if best_col is None:
            best_col = actual_cols[0]
            best_score = 0
        mapping[best_col] = std
        debug.append((std, best_col, best_score))

    print("[cyan]Detected column mapping:[/cyan]")
    for std, ac, sc in sorted(debug, key=lambda x: x[0]):
        print(f"  [bold]{std}[/bold]  <-  '{ac}'  (score {sc})")

    return mapping

@app.command()
def main(
    foundations: Path = typer.Option(..., "--foundations", "-f", help="Path to foundations Excel (xlsx)"),
    faculty: Path = typer.Option(..., "--faculty", "-p", help="Path to faculty Excel (xlsx)"),
    out: Path = typer.Option(Path("outputs/matches.xlsx"), "--out", "-o", help="Output Excel path"),
    score_threshold: int = typer.Option(60, help="Only include matches with score >= this (0-100)"),
    top_n_per_faculty: int = typer.Option(20, help="Max foundations to keep per faculty after filtering")
):
    print(f"[bold]Reading[/bold] foundations from: {foundations}")
    print(f"[bold]Reading[/bold] faculty from: {faculty}")

    fnd = pd.read_excel(foundations)
    fac = pd.read_excel(faculty)

    # Your files’ likely variants (based on what you pasted)
    foundation_required = {
        "Foundation Name": [
            "foundation name", "funder name", "organization", "sponsor", "foundation"
        ],
        "Area of Funding": [
            "area of funding", "areas of funding", "area(s) of funding", "focus areas", "funding area", "keywords"
        ],
        "Average Grant": [
            "average grant", "average grant amount", "typical award", "award size", "funding level", "grant amount"
        ],
        "Career Stage Targeted": [
            "career stage targeted", "career stage", "targeted career stage", "eligibility career stage", "stage"
        ],
        "Deadlines/Restrictions": [
            "deadlines restrictions", "deadlines, restrictions", "deadlines", "restrictions", "notes"
        ],
        "Institution Preference": [
            "institution specific preferences", "institution preference", "us only", "country", "region", "eligibility location"
        ],
        "Website": [
            "website", "website link", "url", "link", "homepage"
        ],
    }
    faculty_required = {
        "Name": ["name", "faculty name"],
        "Degree": ["degree", "degrees"],
        "Rank": ["rank", "academic rank"],
        "Division": ["division", "division ", "dept division", "unit"],
        "Career Stage": ["career stage", "stage", "early/mid/late", "career level"],
        "Keywords": ["keywords", "research keywords", "topics", "interests", "keywords; separated"],
    }

    # Map/rename
    fnd_map = _map_columns_best(fnd, foundation_required)
    fac_map = _map_columns_best(fac, faculty_required)
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

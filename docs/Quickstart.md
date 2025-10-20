# Foundation Matching Tool — Quickstart

## 1. Activate environment
Run these commands in the VS Code terminal:

cd ~/projects/foundation-matching-tool
source .venv/bin/activate

## 2. Run matcher
Unweighted (keywords only):

python main.py --foundations data/foundations.xlsx --faculty data/faculty.xlsx --out outputs/matches_unweighted.xlsx --score-threshold 60

Weighted (adds grant & stage factors):

python main.py --foundations data/foundations.xlsx --faculty data/faculty.xlsx --out outputs/matches_weighted.xlsx --score-threshold 60 --use-weights

## 3. Outputs
- Files written to outputs/
- Match Score (0–100) shows combined fuzzy + weighting score.
- Why Matched (top) explains key keyword pairs and applied weights.

## 4. Notes
- --use-weights blends: 60% keyword, 20% grant level, 20% stage alignment.
- Header mapping tolerant to spaces, commas, punctuation.
- To change thresholds or logic, edit main.py and rerun.

## 5. Version
v0.2 — October 2025

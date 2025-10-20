----- START OF README CONTENT -----
# 🧠 Foundation Matching Tool (FMT)

The **Foundation Matching Tool** is a Python command-line app that matches faculty research keywords to potential foundation funders.  
It uses fuzzy keyword similarity plus optional grant-size and career-stage weighting to produce a ranked list of foundation opportunities.

---

## 🚀 Quick Start

Activate your environment and run the matcher:

```bash
cd ~/projects/foundation-matching-tool
source .venv/bin/activate
python main.py --foundations data/foundations.xlsx --faculty data/faculty.xlsx --out outputs/matches.xlsx --score-threshold 60
python main.py --foundations data/foundations.xlsx --faculty data/faculty.xlsx --out outputs/matches_weighted.xlsx --use-weights
foundation-matching-tool/
├── data/              # input Excel files (foundations, faculty)
├── outputs/           # generated match reports
├── docs/              # PRD, ADR, TDD, Quickstart, etc.
├── prompts/           # Copilot/Codex task prompts
├── src/               # (future) helper modules
├── tests/             # test data & fixtures
└── main.py            # main CLI application
⚙️ Features

Fuzzy keyword matching (rapidfuzz)

Robust header mapping for messy spreadsheets

Optional weighting by grant size and career stage

Clean Excel output with match explanations

Fully documented development workflow (PRD, ADR, TDD)

🧩 Version

v0.2 — October 2025
Author: Lisa Joss-Moore
License: Internal / MIT (your choice)
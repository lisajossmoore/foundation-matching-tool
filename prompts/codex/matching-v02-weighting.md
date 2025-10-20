SYSTEM: You are a senior Python engineer. Keep changes minimal and add tests.
USER GOAL: Add weighting to match scores using Average Grant and Career Stage alignment.
CONTEXT:
- main.py implements fuzzy keyword matching and writes outputs/matches.xlsx.
- Foundations.Average Grant is H/M/L; Faculty.Career Stage vs Foundations.Career Stage Targeted.
REQUIREMENTS:
1) Add optional weights: grant_weight (default 0.2), stage_weight (0.2). Keep keyword_score_weight 0.6.
2) Map H/M/L to 1.0/0.6/0.3; multiply into score if user passes --use-weights.
3) Stage bonus: +10 points if Faculty stage matches (e.g., Early ~ Early).
4) Preserve existing CLI; add flag: --use-weights / --no-use-weights (default off).
5) Update "Why Matched" to note applied weights when on.
6) Add a tiny fixture under tests/data and a unit-style check that weighted score > unweighted for the same pair.
DONE-WHEN:
- CLI runs with and without --use-weights.
- A test script in tests/ demonstrates the diff and prints both scores.

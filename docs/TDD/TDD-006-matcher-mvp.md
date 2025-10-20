# TDD-006: Matcher MVP
## Goal
Given two Excel files (foundations, faculty), produce ranked matches with a fuzzy score and "why matched".

## Inputs
- Foundations.xlsx: Name, Area of Funding (comma keywords), Average Grant (H/M/L), Career Stage Targeted, Deadlines/Restrictions, Institution Preference, Website
- Faculty.xlsx: Name, Degree, Rank, Division, Career Stage, Keywords (semicolon keywords)

## Processing
- Normalize headers (ADR-008).
- Split keywords ("," for foundations, ";" for faculty).
- Score per faculty–foundation using RapidFuzz partial/token_set; keep max score; capture top pairs.

## Outputs
- outputs/matches.xlsx with columns already implemented in main.py.

## Acceptance (v0.1)
- Running the CLI with real files writes a non-empty matches.xlsx.
- Printed "Detected column mapping" is human-plausible.

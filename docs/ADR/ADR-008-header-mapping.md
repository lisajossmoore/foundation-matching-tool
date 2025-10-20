# ADR-008: Header Mapping Strategy
## Context
Source spreadsheets vary: "Foundation name", "area(s) of funding", commas/parentheses/trailing spaces, etc.

## Decision
Normalize headers and choose the best match via fuzzy token ratio + alias lists.
Show the detected mapping in the CLI output for transparency.

## Consequences
- Robust to common human variations.
- Slight risk of wrong auto-map; mitigated by printed mapping and manual review.

## Status
Accepted (v0.1).

# Git Conventions

Inferred from the repository history (last 15 commits on `main`, as of 2026-10-09) unless marked otherwise.

## Commit messages

- **Language:** English.
- **Format:** single-line subject, no body. No Conventional Commits prefixes (none of the sampled commits use `feat:`, `fix:`, `chore:`, etc.).
- **Tense:** mostly past tense (`Added ...`, `Updated ...`, `Separated ...`). One imperative exception (`update claude.md`).
- **Capitalization:** first letter capitalized; trailing period is rare.
- **Example:** `Added import api and protect author deletion when author has a book`
- **Not used:** scopes, ticket IDs, emoji.

## Branches

- **Observed:** only `main` (and `origin/main`). History is linear with no feature branches or merge commits.
- **Merge strategy:** not observable from history (no merges have been made).
- **Branch naming:** no pattern observed. Assumed: `feature/<short-kebab-description>` (assumed, not observed).

## Explicit sources

None found: no `CONTRIBUTING.md`, `.gitmessage`, commitlint/husky config, or `.github/` templates.

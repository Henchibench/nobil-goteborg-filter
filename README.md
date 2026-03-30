# nobil-goteborg-filter

Utilities for inspecting Nobil data and classifying charging stations in Gothenburg as likely public, likely non-public, or needs review.

## Repo secret

Set this in GitHub Actions:

- `NOBIL_API_KEY`

## Local usage

```bash
export NOBIL_API_KEY=...
python3 scripts/nobil_probe.py
```

## Goals

- Inspect actual Nobil v3 response fields
- Identify signals for non-public chargers
- Produce filtered outputs for mapping/review

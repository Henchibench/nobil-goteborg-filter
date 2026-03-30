# nobil-goteborg-filter

Utilities for inspecting Nobil data and classifying charging stations in Gothenburg as likely public, likely non-public, or needs review.

## Repo secret

Set this in GitHub Actions:

- `NOBIL_API_KEY`

## Local usage

```bash
export NOBIL_API_KEY=...
python3 scripts/nobil_probe.py
python3 scripts/build_map.py
```

This writes:
- `output/chargers.geojson`
- `output/summary.json`
- `docs/chargers.geojson`

Open `docs/index.html` in a static server, or use GitHub Pages from the workflow.

## Map classification

The first pass map uses simple heuristics to classify each station:
- `green` = highest likelihood public
- `yellow` = unclear / review
- `red` = likely private or restricted

Each feature stores a `reasons` array so the map can explain why a station got its color.

## Goals

- Inspect actual Nobil v3 response fields
- Identify signals for non-public chargers
- Produce filtered outputs for mapping/review
- Publish a review map for Gothenburg chargers

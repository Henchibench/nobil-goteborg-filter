# Nobil Gothenburg Charger Map — Design Spec

## Context

We need to identify which EV chargers in the Gothenburg area (from the NOBIL API) are truly publicly accessible vs private/restricted. The existing project fetches station data, classifies stations with a scoring system (green/yellow/red), and renders a basic Leaflet map. This redesign adds satellite imagery for visual verification, manual flagging of non-public stations, and export of flagged stations.

## What We're Building

An enhanced single-page map application served via GitHub Pages (`docs/index.html`) that lets a reviewer:

1. View all chargers on a satellite map to visually assess public accessibility
2. See detailed station info by clicking markers
3. Manually flag stations as "not public" via checkboxes
4. Export the flagged stations as CSV or JSON
5. Filter the map by classification color

## Architecture

- **Backend**: `scripts/build_map.py` (Python, stdlib only) — fetches from NOBIL API, classifies, outputs GeoJSON
- **Frontend**: `docs/index.html` — single-page Leaflet app, no build step
- **Data**: `docs/chargers.geojson` — static GeoJSON consumed by the frontend
- **Deployment**: GitHub Pages from `docs/` directory, built via `.github/workflows/build-map.yml`

## Changes Required

### 1. `scripts/build_map.py` — Add Connector Details to GeoJSON

**File**: `scripts/build_map.py`

Add these fields to each feature's `properties` in `build_feature()`:

- `connector_types`: list of connector type strings (from attr conn `attrtypeid=4`, e.g. "Type 2", "CCS", "Hydrogen")
- `charging_capacity`: list of capacity strings (from attr conn `attrtypeid=5`, e.g. "50 kW", "700 bar")
- `energy_carrier`: list of energy carrier strings (from attr conn `attrtypeid=26`, e.g. "Electric", "Hydrogen")
- `parking_fee`: string from station attr `attrtypeid=7` trans value
- `time_limit`: string from station attr `attrtypeid=6` trans value

Reuse existing helper `get_connector_trans_values()` for connector-level fields and `get_station_attr_trans()` for station-level fields.

### 2. `docs/index.html` — Enhanced Frontend

#### 2a. Satellite Layer Toggle

Add Esri World Imagery as a base layer alongside OpenStreetMap using `L.control.layers`:

- OpenStreetMap (street) — existing tile layer
- Esri World Imagery (satellite) — `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`
- Default to satellite view since the primary use case is visual verification

#### 2b. Enhanced Station Info Panel

When a marker is clicked, the side panel shows:

- Station name and full address (street, house number, zipcode, city)
- Owner and operator
- Number of charging points / available
- Connector types and charging capacity (new fields from build_map.py)
- Energy carrier
- Availability status, Open 24h, parking fee, time limit
- Classification badge (colored dot + label) with score
- List of classification reasons
- **Checkbox**: "Flag as not public" — toggles this station's flagged state

#### 2c. Flagging System

- Store flagged station IDs in `localStorage` under key `flaggedStations` as a JSON array of station IDs
- On page load, read localStorage and apply flagged state to markers
- Flagged markers get reduced opacity (0.4) to visually distinguish them
- Side panel shows a counter: "X stations flagged as not public"
- A "Clear all flags" button to reset

#### 2d. Export Buttons

Two buttons in the side panel below the flagged counter:

**Export CSV**: Downloads `flagged-chargers.csv` with columns:
- id, name, street, house_number, zipcode, city, owner, operator, charging_points, connector_types, classification, score

**Export JSON**: Downloads `flagged-chargers.json` as an array of objects with the same fields.

Both use `Blob` + `URL.createObjectURL` + programmatic `<a>` click for download. No server needed.

#### 2e. Classification Filter Toggles

Three toggle buttons (green/yellow/red) in the side panel that show/hide markers by classification. All active by default. Clicking toggles visibility of that classification's markers on the map.

#### 2f. Design

Use the `/frontend-design` skill during implementation for a polished, production-grade UI. Maintain the existing Swedish-language interface. Keep the glassmorphism card style but modernize as needed.

### 3. No Changes to GitHub Actions

The existing workflows (`build-map.yml`, `nobil-probe.yml`) already handle:
- Running `build_map.py` to generate GeoJSON
- Deploying `docs/` to GitHub Pages
- No changes needed since we're only modifying files the workflows already process.

## Data Flow

```
NOBIL API → build_map.py → docs/chargers.geojson → index.html (Leaflet)
                                                         ↓
                                                   localStorage (flags)
                                                         ↓
                                                   CSV/JSON export
```

## Verification

1. **Run build_map.py locally**: `NOBIL_API_KEY=<key> python scripts/build_map.py` — verify new fields appear in `output/chargers.geojson`
2. **Open docs/index.html in browser**: Serve with `python -m http.server -d docs 8000`, verify:
   - Satellite layer toggle works
   - Markers render with correct colors
   - Clicking a marker shows full info including new fields
   - Checkbox flags station, persists on reload
   - Filter toggles hide/show correct markers
   - Export CSV and JSON contain flagged stations only
3. **GitHub Pages**: Push to main, verify deployed site works

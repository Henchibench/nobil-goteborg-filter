#!/usr/bin/env python3
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

API_KEY = os.getenv('NOBIL_API_KEY', '').strip()
if not API_KEY:
    print('Missing NOBIL_API_KEY', file=sys.stderr)
    sys.exit(2)

ENDPOINT = 'https://nobil.no/api/server/search.php'
OUTPUT_DIR = Path('output')
DOCS_DIR = Path('docs')

# Slightly larger rectangle around Gothenburg metro area.
PARAMS = {
    'apikey': API_KEY,
    'apiversion': '3',
    'action': 'search',
    'type': 'rectangle',
    'northeast': '(57.9000, 12.2500)',
    'southwest': '(57.5000, 11.7000)',
    'limit': '5000',
    'format': 'json',
}

PRIVATE_HINTS = [
    'brf', 'bostadsrätt', 'bostad', 'residents', 'boende', 'personal', 'staff',
    'private', 'privat', 'intern', 'internal', 'depot', 'depå', 'fleet',
    'företag', 'company', 'medlemm', 'members only', 'gästparkering',
    'hotel guests', 'hotellgäster', 'kundparkering', 'garage', 'leasing',
]
PUBLIC_HINTS = [
    'parkering göteborg', 'göteborgs stads parkering', 'okq8', 'circle k',
    'mer', 'charge node', 'eviny', 'ionity', 'tesla supercharger',
    'shopping', 'köpcentrum', 'publik', 'allmän', 'centrum', 'hamn',
    'station', 'resecentrum', 'transport hub', 'p-hus', 'parking'
]


def post_json(params):
    encoded = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        ENDPOINT,
        data=encoded.encode('utf-8'),
        headers={
            'User-Agent': 'nobil-goteborg-filter/0.3',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8', errors='replace'))


def parse_position(pos):
    if not pos:
        return None, None
    m = re.match(r'^\(([-0-9.]+),\s*([-0-9.]+)\)$', str(pos).strip())
    if not m:
        return None, None
    return float(m.group(1)), float(m.group(2))


def flatten_station_text(csmd):
    fields = [
        csmd.get('name'), csmd.get('Owned_by'), csmd.get('Operator'),
        csmd.get('Description_of_location'), csmd.get('User_comment'),
        csmd.get('Street'), csmd.get('City')
    ]
    return ' | '.join(str(v) for v in fields if v).lower()


def get_station_attr(station, attr_type_id):
    return ((station.get('attr') or {}).get('st') or {}).get(str(attr_type_id))


def get_station_attr_trans(station, attr_type_id):
    attr = get_station_attr(station, attr_type_id)
    return (attr or {}).get('trans')


def get_connector_trans_values(station, attr_type_id):
    conn = ((station.get('attr') or {}).get('conn') or {})
    values = []
    for _, attrs in conn.items():
        if not isinstance(attrs, dict):
            continue
        attr = attrs.get(str(attr_type_id))
        if isinstance(attr, dict) and attr.get('trans'):
            values.append(attr['trans'])
    return sorted(set(values))


def classify_station(station):
    csmd = station.get('csmd') or {}
    text = flatten_station_text(csmd)
    reasons = []
    score = 0

    availability = get_station_attr_trans(station, 2)
    location = get_station_attr_trans(station, 3)
    open24 = get_station_attr_trans(station, 24)
    realtime = get_station_attr_trans(station, 21)
    accessibility_values = get_connector_trans_values(station, 1)
    payment_values = get_connector_trans_values(station, 19)

    if availability == 'Public':
        score += 3
        reasons.append('Availability=Public')
    elif availability:
        score -= 3
        reasons.append(f'Availability={availability}')
    else:
        reasons.append('Availability saknas')

    if accessibility_values:
        if all(v == 'Open' for v in accessibility_values):
            score += 2
            reasons.append('Accessibility=Open på alla connectors')
        elif any(v != 'Open' for v in accessibility_values):
            score -= 2
            reasons.append(f'Accessibility blandad/begränsad: {", ".join(accessibility_values)}')
    else:
        reasons.append('Accessibility saknas')

    if location in {'Transport hub', 'Shopping center', 'Street side', 'Parking garage'}:
        score += 1
        reasons.append(f'Location={location}')
    elif location:
        reasons.append(f'Location={location}')

    if open24 == 'Yes':
        score += 1
        reasons.append('Open 24h=Yes')
    if realtime == 'Yes':
        score += 1
        reasons.append('Real-time information=Yes')
    if payment_values:
        reasons.append('Payment=' + ', '.join(payment_values))

    for hint in PRIVATE_HINTS:
        if hint in text:
            score -= 3
            reasons.append(f'Privat signalord: {hint}')
            break

    for hint in PUBLIC_HINTS:
        if hint in text:
            score += 1
            reasons.append(f'Publik signalord: {hint}')
            break

    owned_by = (csmd.get('Owned_by') or '').lower()
    operator = (csmd.get('Operator') or '').lower()
    if 'stads parkering' in owned_by or 'stads parkering' in operator:
        score += 2
        reasons.append('Kommunal parkering-signal')

    if score >= 4:
        cls = 'green'
        label = 'Högst trolig publik'
    elif score <= 0:
        cls = 'red'
        label = 'Sannolikt privat'
    else:
        cls = 'yellow'
        label = 'Något oklar'

    return {
        'classification': cls,
        'classification_label': label,
        'score': score,
        'reasons': reasons,
        'signals': {
            'availability': availability,
            'location': location,
            'open24': open24,
            'realtime': realtime,
            'accessibility': accessibility_values,
            'payment': payment_values,
        },
    }


def build_feature(station):
    csmd = station.get('csmd') or {}
    lat, lon = parse_position(csmd.get('Position'))
    if lat is None or lon is None:
        return None

    classified = classify_station(station)
    props = {
        'id': csmd.get('id'),
        'name': csmd.get('name'),
        'street': csmd.get('Street'),
        'house_number': csmd.get('House_number'),
        'zipcode': csmd.get('Zipcode'),
        'city': csmd.get('City'),
        'owned_by': csmd.get('Owned_by'),
        'operator': csmd.get('Operator'),
        'description_of_location': csmd.get('Description_of_location'),
        'user_comment': csmd.get('User_comment'),
        'contact_info': csmd.get('Contact_info'),
        'number_charging_points': csmd.get('Number_charging_points'),
        'available_charging_points': csmd.get('Available_charging_points'),
        'station_status': csmd.get('Station_status'),
        'international_id': csmd.get('International_id'),
    }
    props.update(classified)

    return {
        'type': 'Feature',
        'geometry': {
            'type': 'Point',
            'coordinates': [lon, lat],
        },
        'properties': props,
    }


def main():
    data = post_json(PARAMS)
    stations = data.get('chargerstations') or []
    features = []
    skipped = 0
    counts = {'green': 0, 'yellow': 0, 'red': 0}

    for station in stations:
        feature = build_feature(station)
        if not feature:
            skipped += 1
            continue
        counts[feature['properties']['classification']] += 1
        features.append(feature)

    fc = {
        'type': 'FeatureCollection',
        'features': features,
        'meta': {
            'provider': data.get('Provider'),
            'rights': data.get('Rights'),
            'apiver': data.get('apiver'),
            'station_count_raw': len(stations),
            'station_count_mapped': len(features),
            'station_count_skipped': skipped,
            'classification_counts': counts,
            'request': {k: ('***' if k == 'apikey' else v) for k, v in PARAMS.items()},
        }
    }

    OUTPUT_DIR.mkdir(exist_ok=True)
    DOCS_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / 'chargers.geojson').write_text(json.dumps(fc, ensure_ascii=False, indent=2))
    (OUTPUT_DIR / 'summary.json').write_text(json.dumps(fc['meta'], ensure_ascii=False, indent=2))
    (DOCS_DIR / 'chargers.geojson').write_text(json.dumps(fc, ensure_ascii=False))
    print(json.dumps(fc['meta'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

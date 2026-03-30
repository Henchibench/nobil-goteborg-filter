#!/usr/bin/env python3
import json, os, sys, urllib.parse, urllib.request

API_KEY = os.getenv('NOBIL_API_KEY', '').strip()
if not API_KEY:
    print('Missing NOBIL_API_KEY', file=sys.stderr)
    sys.exit(2)

# Based on Nobil API v3 documentation.
endpoint = 'https://nobil.no/api/server/search.php'
params = {
    'apikey': API_KEY,
    'apiversion': '3',
    'action': 'search',
    'type': 'rectangle',
    # Rough rectangle around central Gothenburg.
    'northeast': '(57.7640, 12.0970)',
    'southwest': '(57.6400, 11.8200)',
    'limit': '5',
    'format': 'json',
}
encoded = urllib.parse.urlencode(params)
req = urllib.request.Request(
    endpoint,
    data=encoded.encode('utf-8'),
    headers={
        'User-Agent': 'nobil-goteborg-filter/0.2',
        'Content-Type': 'application/x-www-form-urlencoded',
    },
    method='POST',
)
with urllib.request.urlopen(req, timeout=30) as r:
    body = r.read().decode('utf-8', errors='replace')

result = {
    'request_url': endpoint,
    'request_params': {k: ('***' if k == 'apikey' else v) for k, v in params.items()},
    'body_preview': body[:4000],
}

try:
    data = json.loads(body)
    result['parsed_json'] = True
    result['json_type'] = type(data).__name__
    if isinstance(data, dict):
        result['json_top_level_keys'] = sorted(list(data.keys()))
        stations = None
        for key in ['chargerstations', 'stations', 'results', 'data']:
            if key in data and isinstance(data[key], list):
                stations = data[key]
                result['station_list_key'] = key
                break
        if stations:
            result['station_count'] = len(stations)
            first = stations[0]
            if isinstance(first, dict):
                result['first_station_keys'] = sorted(first.keys())
                # Keep a tiny sample of first station for field discovery.
                result['first_station_sample'] = {
                    k: first[k] for k in list(first.keys())[:20]
                }
    elif isinstance(data, list):
        result['list_length'] = len(data)
        if data and isinstance(data[0], dict):
            result['first_station_keys'] = sorted(data[0].keys())
            result['first_station_sample'] = {
                k: data[0][k] for k in list(data[0].keys())[:20]
            }
except Exception as e:
    result['parsed_json'] = False
    result['parse_error'] = str(e)

os.makedirs('output', exist_ok=True)
with open('output/probe.json', 'w') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(json.dumps(result, indent=2, ensure_ascii=False))

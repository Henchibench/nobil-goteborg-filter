#!/usr/bin/env python3
import json, os, sys, urllib.parse, urllib.request

API_KEY = os.getenv('NOBIL_API_KEY', '').strip()
if not API_KEY:
    print('Missing NOBIL_API_KEY', file=sys.stderr)
    sys.exit(2)

# NOTE: request shape may need adjustment once we confirm the exact live API behavior.
params = {
    'lat': '57.7089',
    'lng': '11.9746',
    'distance': '8',
    'limit': '3',
    'json': 'true',
    'yourapikey': API_KEY,
}
url = 'https://www.nobil.no/api/client/search_apiVer3.php?' + urllib.parse.urlencode(params)
req = urllib.request.Request(url, headers={'User-Agent': 'nobil-goteborg-filter/0.1'})
with urllib.request.urlopen(req, timeout=30) as r:
    body = r.read().decode('utf-8', errors='replace')

result = {
    'request_url': url.replace(API_KEY, '***'),
    'body_preview': body[:4000],
}

try:
    data = json.loads(body)
    result['json_top_level_keys'] = sorted(list(data.keys())) if isinstance(data, dict) else None
    if isinstance(data, dict):
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
    result['parsed_json'] = True
except Exception as e:
    result['parsed_json'] = False
    result['parse_error'] = str(e)

os.makedirs('output', exist_ok=True)
with open('output/probe.json', 'w') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(json.dumps(result, indent=2, ensure_ascii=False))

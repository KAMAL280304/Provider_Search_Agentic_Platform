import json

roles = json.load(open('app/fhir/data/practitioner_roles.json'))['practitionerRoles']
pracs = {}
for p in json.load(open('app/fhir/data/practitioners.json'))['practitioners']:
    npi = p['identifier'][0]['value']
    pracs[npi] = p
locs = {}
for l in json.load(open('app/fhir/data/locations.json'))['locations']:
    lid = l['id'].replace('loc-', '')
    locs[lid] = l

pcp_codes = ['207Q00000X', '207R00000X', '208D00000X', '207P00000X']

for r in roles:
    code = r['specialty'][0]['coding'][0]['code']
    disp = r['specialty'][0]['coding'][0]['display']
    if code in pcp_codes:
        npi = r['id'].replace('role-', '')
        p = pracs.get(npi, {})
        loc = locs.get(npi, {})
        city = loc.get('address', {}).get('city', '?')
        state = loc.get('address', {}).get('state', '?')
        nm = p.get('name', [{}])[0]
        name = nm.get('given', [''])[0] + ' ' + nm.get('family', '')
        plans = next((e['valueString'] for e in r.get('extension', []) if e['url'] == 'network-plans'), '')
        print(f"{npi}|{name.strip()}|{disp}|{city}|{state}|{plans}")

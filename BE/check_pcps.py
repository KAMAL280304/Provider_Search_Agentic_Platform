import json

roles = json.load(open('app/fhir/data/practitioner_roles.json'))['practitionerRoles']
pracs = {p['identifier'][0]['value']: p for p in json.load(open('app/fhir/data/practitioners.json'))['practitioners']}
locs  = {l['id'].replace('loc-', ''): l for l in json.load(open('app/fhir/data/locations.json'))['locations']}

check_npis = ['1821267477', '1861062960', '1417215757', '1619394558', '1386176139', '1194730242']

for npi in check_npis:
    role = next((r for r in roles if r['id'] == f'role-{npi}'), None)
    prac = pracs.get(npi, {})
    loc  = locs.get(npi, {})
    nm   = prac.get('name', [{}])[0]
    name = nm.get('given', [''])[0] + ' ' + nm.get('family', '')
    city = loc.get('address', {}).get('city', '?')
    state = loc.get('address', {}).get('state', '?')
    if role:
        plans = next((e['valueString'] for e in role.get('extension', []) if e['url'] == 'network-plans'), '')
        spec  = role['specialty'][0]['coding'][0]['display']
        print(f"NPI:{npi} | {name.strip()} | {spec} | {city},{state}")
        print(f"  Plans: {plans}")
    else:
        print(f"NPI:{npi} | {name.strip()} | {city},{state} | NO ROLE")

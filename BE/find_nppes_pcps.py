import requests, json

def search_individual_pcps(state, city, taxonomy, limit=10):
    url = (
        f"https://npiregistry.cms.hhs.gov/api/?version=2.1"
        f"&enumeration_type=NPI-1"
        f"&taxonomy_description={taxonomy.replace(' ', '+')}"
        f"&state={state}&city={city.replace(' ', '+')}&limit={limit}&skip=0"
    )
    r = requests.get(url, timeout=15)
    data = r.json()
    results = []
    for p in data.get('results', []):
        npi = p['number']
        basic = p.get('basic', {})
        name = basic.get('first_name', '') + ' ' + basic.get('last_name', '')
        cred = basic.get('credential', '')
        addrs = p.get('addresses', [{}])
        addr = next((a for a in addrs if a.get('address_purpose') == 'LOCATION'), addrs[0] if addrs else {})
        city_r = addr.get('city', '')
        state_r = addr.get('state', '')
        addr_line = addr.get('address_1', '')
        zip_r = addr.get('postal_code', '')[:5]
        lat = addr.get('latitude', '')
        lon = addr.get('longitude', '')
        results.append({
            'npi': npi, 'name': name.strip(), 'credential': cred,
            'city': city_r, 'state': state_r, 'address': addr_line,
            'zip': zip_r, 'lat': lat, 'lon': lon
        })
    return results

for label, state, city, tax in [
    ("Chicago Family Medicine", "IL", "Chicago", "Family Medicine"),
    ("Chicago Internal Medicine", "IL", "Chicago", "Internal Medicine"),
    ("New York Family Medicine", "NY", "New York", "Family Medicine"),
    ("New York Internal Medicine", "NY", "New York", "Internal Medicine"),
]:
    print(f"\n=== {label} ===")
    for p in search_individual_pcps(state, city, tax, limit=8):
        if p['name']:
            print(f"  NPI:{p['npi']} | {p['name']} {p['credential']} | {p['address']}, {p['city']}, {p['state']} {p['zip']}")

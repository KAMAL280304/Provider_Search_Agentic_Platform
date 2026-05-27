import json

roles = json.load(open('app/fhir/data/practitioner_roles.json'))['practitionerRoles']
locs  = json.load(open('app/fhir/data/locations.json'))['locations']
pracs = json.load(open('app/fhir/data/practitioners.json'))['practitioners']

r = next((x for x in roles if x['id'] == 'role-1043899545'), None)
l = next((x for x in locs  if x['id'] == 'loc-1043899545'),  None)
p = next((x for x in pracs if x['id'] == 'prac-1043899545'), None)
print('Chicago PCP role :', r['id'] if r else 'MISSING')
print('Chicago PCP loc  :', l['address']['city'] if l else 'MISSING')
print('Chicago PCP prac :', p['name'][0]['family'] if p else 'MISSING')

mb = next((x for x in roles if x['id'] == 'role-1194730242'), None)
plans = next((e['valueString'] for e in mb['extension'] if e['url'] == 'network-plans'), '')
print('Maya Bledsoe plans:', plans)

from app.db.repositories.user_repo import UserRepository
repo = UserRepository()
for mid in ['MEM-10001','MEM-10002','MEM-10003','MEM-10004','MEM-10005','MEM-10006']:
    u = repo.get_by_id(mid)
    pcp = u.assigned_pcp
    print(f"{u.first_name} {u.last_name} | age={u.age} | PCP={pcp.get('name')} | NPI={pcp.get('npi')}")

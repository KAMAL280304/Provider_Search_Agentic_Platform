"""
FHIR Directory Seeder
=====================
Adds realistic providers to the FHIR directory so that every
specialty × city × plan combination has at least 3 in-network providers.

Usage:
    python seed_fhir_data.py                  # preview what will be added
    python seed_fhir_data.py --apply          # write changes to disk
    python seed_fhir_data.py --apply --reset  # wipe seed entries and re-seed fresh

Seeded entries are tagged with  "seeded": true  so --reset can remove them cleanly.
"""

import argparse
import json
import random
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "app" / "fhir" / "data"

# ── All plan IDs used in _PLAN_RULES ──────────────────────────────────────────
ALL_PLANS = [
    "plan-cigna-gold",      # Cigna True Choice Medicare PPO
    "plan-bcbs-platinum",   # Cigna True Choice Access Medicare PPO
    "plan-star-gold",       # Cigna Total Care Plus HMO D-SNP  ← James's plan
    "plan-aetna-gold",      # Cigna Total Care HMO D-SNP
    "plan-united-platinum", # Cigna Preferred Medicare HMO
]

# ── City → state + ZIP + coordinates ──────────────────────────────────────────
CITIES = {
    "New York":    {"state": "NY", "zip": "10016", "lat": 40.7459, "lon": -73.9781,
                    "addresses": [
                        ("550 1st Ave",       "10016"),
                        ("635 Madison Ave",   "10022"),
                        ("1275 York Ave",     "10065"),
                        ("525 E 68th St",     "10065"),
                        ("240 E 38th St",     "10016"),
                        ("317 E 34th St",     "10016"),
                        ("160 E 32nd St",     "10016"),
                        ("115 E 61st St",     "10065"),
                        ("77 Water St",       "10005"),
                        ("222 W 14th St",     "10011"),
                    ]},
    "Los Angeles": {"state": "CA", "zip": "90024", "lat": 34.0635, "lon": -118.4318,
                    "addresses": [
                        ("100 UCLA Medical Plz", "90095"),
                        ("8700 Beverly Blvd",    "90048"),
                        ("1245 16th St",         "90404"),
                        ("2001 Santa Monica Blvd","90404"),
                        ("3000 W Olympic Blvd",  "90006"),
                        ("4650 W Sunset Blvd",   "90027"),
                        ("1200 N State St",      "90033"),
                        ("7601 Imperial Hwy",    "90242"),
                        ("600 S Garfield Ave",   "91801"),
                        ("425 S Alvarado St",    "90057"),
                    ]},
    "Miami":       {"state": "FL", "zip": "33131", "lat": 25.7650, "lon": -80.1890,
                    "addresses": [
                        ("1400 NW 12th Ave",     "33136"),
                        ("8900 N Kendall Dr",    "33176"),
                        ("3661 S Miami Ave",     "33133"),
                        ("1321 NW 14th St",      "33125"),
                        ("200 SE 1st St",        "33131"),
                        ("21110 Biscayne Blvd",  "33180"),
                        ("11410 N Kendall Dr",   "33176"),
                        ("900 NW 17th St",       "33136"),
                        ("5333 N Dixie Hwy",     "33166"),
                        ("7800 SW 87th Ave",     "33173"),
                    ]},
    "Chicago":     {"state": "IL", "zip": "60611", "lat": 41.8930, "lon": -87.6180,
                    "addresses": [
                        ("251 E Huron St",       "60611"),
                        ("676 N St Clair St",    "60611"),
                        ("1725 W Harrison St",   "60612"),
                        ("2650 Ridge Ave",       "60201"),
                        ("5841 S Maryland Ave",  "60637"),
                        ("800 Austin Blvd",      "60304"),
                        ("1000 N Westmoreland",  "60093"),
                        ("1001 Superior St",     "60611"),
                        ("1500 N Halsted St",    "60642"),
                        ("2160 S 1st Ave",       "60153"),
                    ]},
    "Houston":     {"state": "TX", "zip": "77030", "lat": 29.7070, "lon": -95.3980,
                    "addresses": [
                        ("6560 Fannin St",       "77030"),
                        ("1709 Dryden Rd",       "77030"),
                        ("7737 Southwest Fwy",   "77074"),
                        ("2727 W Holcombe",      "77025"),
                        ("18220 TX-249",         "77070"),
                        ("1315 Calhoun Rd",      "77004"),
                        ("4126 Southwest Fwy",   "77027"),
                        ("11800 Astoria Blvd",   "77089"),
                        ("19951 Park Row Dr",    "77084"),
                        ("3000 Weslayan St",     "77027"),
                    ]},
    "Seattle":     {"state": "WA", "zip": "98101", "lat": 47.6062, "lon": -122.3321,
                    "addresses": [
                        ("4245 Roosevelt Way NE","98115"),
                        ("1959 NE Pacific St",   "98195"),
                        ("800 5th Ave",          "98104"),
                        ("600 Broadway",         "98122"),
                        ("10500 NE 8th St",      "98004"),
                        ("12844 Military Rd S",  "98168"),
                        ("1229 Madison St",      "98104"),
                        ("550 17th Ave",         "98122"),
                        ("4540 Sand Point Way NE","98105"),
                        ("6330 Fauntleroy Way SW","98136"),
                    ]},
}

# ── Specialties to seed: NUCC code + display name ─────────────────────────────
SPECIALTIES = [
    ("207X00000X", "Orthopaedic Surgery"),
    ("207RC0000X", "Internal Medicine, Cardiovascular Disease"),
    ("2084N0400X", "Psychiatry & Neurology, Neurology"),
    ("207N00000X", "Dermatology"),
    ("207RG0100X", "Internal Medicine, Gastroenterology"),
    ("207RR0500X", "Internal Medicine, Rheumatology"),
    ("207RE0101X", "Internal Medicine, Endocrinology, Diabetes & Metabolism"),
    ("207RP1001X", "Internal Medicine, Pulmonary Disease"),
    ("208800000X", "Urology"),
    ("207W00000X", "Ophthalmology"),
    ("207Y00000X", "Otolaryngology"),
    ("2084P0800X", "Psychiatry & Neurology, Psychiatry"),
    ("207Q00000X", "Family Medicine"),
    ("207R00000X", "Internal Medicine"),
    ("2085R0202X", "Diagnostic Radiology"),
]

# ── Hospital / clinic names per city ─────────────────────────────────────────
ORG_NAMES = {
    "New York":    ["NYU Langone Health", "Mount Sinai Hospital", "NewYork-Presbyterian",
                    "Weill Cornell Medicine", "Lenox Hill Hospital", "Memorial Sloan Kettering",
                    "Montefiore Medical Center", "Northwell Health"],
    "Los Angeles": ["UCLA Health", "Cedars-Sinai Medical Center", "Keck Medicine of USC",
                    "Providence Health", "Kaiser Permanente LA", "Huntington Health",
                    "Dignity Health", "Los Angeles County Hospital"],
    "Miami":       ["Jackson Health System", "Baptist Health South Florida", "University of Miami Health",
                    "Cleveland Clinic Florida", "Memorial Healthcare", "Nicklaus Children's",
                    "Mount Sinai Medical Center Miami", "HCA Florida"],
    "Chicago":     ["Northwestern Memorial Hospital", "Rush University Medical Center",
                    "University of Chicago Medicine", "Advocate Health", "NorthShore University",
                    "Loyola University Medical Center", "AMITA Health", "Lurie Children's Hospital"],
    "Houston":     ["Houston Methodist", "Memorial Hermann", "Texas Medical Center",
                    "UTHealth Houston", "Baylor St. Luke's", "HCA Houston Healthcare",
                    "CHI St. Luke's Health", "Texas Children's Hospital"],
    "Seattle":     ["UW Medicine", "Swedish Health Services", "Virginia Mason Medical Center",
                    "MultiCare Health System", "Providence Health Seattle",
                    "Overlake Medical Center", "Harborview Medical Center", "Group Health Seattle"],
}

# ── First/last name pools ─────────────────────────────────────────────────────
FIRST_NAMES_M = ["James","Robert","Michael","David","John","William","Richard","Charles",
                  "Joseph","Thomas","Daniel","Matthew","Anthony","Donald","Steven","Mark",
                  "Paul","Andrew","Joshua","Kevin","Brian","George","Edward","Ronald","Timothy"]
FIRST_NAMES_F = ["Mary","Patricia","Jennifer","Linda","Barbara","Susan","Dorothy","Sarah",
                  "Karen","Lisa","Nancy","Betty","Sandra","Margaret","Ashley","Kimberly",
                  "Emily","Donna","Michelle","Carol","Amanda","Melissa","Deborah","Stephanie","Rebecca"]
LAST_NAMES = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez",
               "Martinez","Hernandez","Lopez","Gonzalez","Wilson","Anderson","Taylor","Thomas",
               "Jackson","White","Harris","Sanchez","Clark","Ramirez","Lewis","Robinson","Walker",
               "Young","Allen","King","Wright","Scott","Torres","Nguyen","Hill","Flores","Green",
               "Adams","Nelson","Baker","Hall","Rivera","Campbell","Mitchell","Carter","Roberts",
               "Patel","Gupta","Khan","Singh","Chen","Wang","Li","Kim","Park","Yamamoto","Cohen"]

LANGUAGES_POOL = [
    ["English"], ["English", "Spanish"], ["English", "Mandarin"],
    ["English", "Hindi"], ["English", "French"], ["English", "Portuguese"],
    ["English", "Korean"], ["English", "Arabic"], ["English", "Russian"],
]


def _make_npi() -> str:
    """Generate a plausible fake NPI (10 digits, starts with 1)."""
    return "1" + "".join([str(random.randint(0, 9)) for _ in range(9)])


def _make_provider(npi: str, first: str, last: str, city_key: str,
                   addr_line: str, zip_code: str, org_id: str,
                   specialty_code: str, specialty_display: str,
                   plans: list[str], telehealth: bool, gender: str) -> tuple[dict, dict, dict]:
    """Returns (practitioner, location, role) dicts."""
    city_info = CITIES[city_key]
    loc_id  = f"loc-{npi}"
    prac_id = f"prac-{npi}"

    practitioner = {
        "resourceType": "Practitioner",
        "id": prac_id,
        "identifier": [{"system": "http://hl7.org/fhir/sid/us-npi", "value": npi}],
        "name": [{"family": last.upper(), "given": [first.upper()]}],
    }

    location = {
        "resourceType": "Location",
        "id": loc_id,
        "address": {
            "line": [addr_line],
            "city": city_key,
            "state": city_info["state"],
            "postalCode": zip_code,
        },
        "position": {
            "latitude":  city_info["lat"] + random.uniform(-0.02, 0.02),
            "longitude": city_info["lon"] + random.uniform(-0.02, 0.02),
        },
    }

    role = {
        "resourceType": "PractitionerRole",
        "id": f"role-{npi}",
        "active": True,
        "seeded": True,   # marker so --reset can remove them
        "practitioner": {"reference": f"Practitioner/{prac_id}"},
        "organization":  {"reference": f"Organization/{org_id}"},
        "location": [{"reference": f"Location/{loc_id}"}],
        "specialty": [{
            "coding": [{
                "system": "http://nucc.org/provider-taxonomy",
                "code":    specialty_code,
                "display": specialty_display,
            }]
        }],
        "extension": [
            {"url": "network-plans",       "valueString": ",".join(plans)},
            {"url": "telehealth_available","valueBoolean": telehealth},
            {"url": "accepting_new_patients","valueBoolean": True},
            {"url": "languages",           "valueString": ",".join(random.choice(LANGUAGES_POOL))},
            {"url": "gender",              "valueString": gender},
        ],
    }
    return practitioner, location, role


def _org_id(city_key: str, org_name: str) -> str:
    slug = org_name.lower().replace(" ", "-").replace("'", "").replace(",", "")[:20]
    return f"org-{slug}"


def load_data():
    def _load(name):
        with open(DATA_DIR / name) as f:
            return json.load(f)
    roles_raw   = _load("practitioner_roles.json")
    pracs_raw   = _load("practitioners.json")
    locs_raw    = _load("locations.json")
    orgs_raw    = _load("organizations.json")
    plans_raw   = _load("insurance_plans.json")
    return roles_raw, pracs_raw, locs_raw, orgs_raw, plans_raw


def save_data(roles_raw, pracs_raw, locs_raw, orgs_raw):
    def _save(name, data):
        with open(DATA_DIR / name, "w") as f:
            json.dump(data, f, indent=2)
    _save("practitioner_roles.json", roles_raw)
    _save("practitioners.json",      pracs_raw)
    _save("locations.json",          locs_raw)
    _save("organizations.json",      orgs_raw)


def analyze_gaps(roles_raw, locs_raw):
    """Return set of (specialty_display, city, plan_id) tuples that have < 3 in-network providers."""
    roles = roles_raw["practitionerRoles"]
    locs  = {l["id"]: l for l in locs_raw["locations"]}

    # Build coverage map: (specialty, city, plan) → count
    coverage: dict[tuple, int] = {}

    for r in roles:
        city = ""
        for loc_ref in r.get("location", []):
            loc_id = loc_ref["reference"].split("/")[-1]
            loc = locs.get(loc_id, {})
            city = loc.get("address", {}).get("city", "")
            if city:
                break

        plans_str = ""
        for ext in r.get("extension", []):
            if ext.get("url") == "network-plans":
                plans_str = ext.get("valueString", "")

        for s in r.get("specialty", []):
            for coding in s.get("coding", []):
                spec = coding.get("display", "")
                for plan in plans_str.split(","):
                    plan = plan.strip()
                    if city and spec and plan:
                        key = (spec, city, plan)
                        coverage[key] = coverage.get(key, 0) + 1

    gaps = []
    for spec_code, spec_display in SPECIALTIES:
        for city in CITIES:
            for plan in ALL_PLANS:
                key = (spec_display, city, plan)
                current = coverage.get(key, 0)
                if current < 3:
                    gaps.append({
                        "specialty_code":    spec_code,
                        "specialty_display": spec_display,
                        "city":              city,
                        "plan":              plan,
                        "current_count":     current,
                        "need":              3 - current,
                    })
    return gaps


def main():
    parser = argparse.ArgumentParser(description="Seed FHIR directory with in-network providers")
    parser.add_argument("--apply",  action="store_true", help="Write changes to disk")
    parser.add_argument("--reset",  action="store_true", help="Remove previously seeded entries first")
    parser.add_argument("--min",    type=int, default=3,  help="Minimum providers per specialty/city/plan (default 3)")
    args = parser.parse_args()

    random.seed(42)

    roles_raw, pracs_raw, locs_raw, orgs_raw, plans_raw = load_data()

    # ── Optional reset ────────────────────────────────────────────────────────
    if args.reset:
        before = len(roles_raw["practitionerRoles"])
        roles_raw["practitionerRoles"] = [r for r in roles_raw["practitionerRoles"] if not r.get("seeded")]
        removed = before - len(roles_raw["practitionerRoles"])
        # Build set of seeded NPI IDs
        remaining_prac_ids = {r["practitioner"]["reference"].split("/")[-1]
                              for r in roles_raw["practitionerRoles"]}
        pracs_raw["practitioners"] = [p for p in pracs_raw["practitioners"]
                                      if p["id"] in remaining_prac_ids or not p["id"].startswith("prac-1") ]
        remaining_loc_ids = {lr["reference"].split("/")[-1]
                             for r in roles_raw["practitionerRoles"]
                             for lr in r.get("location", [])}
        locs_raw["locations"] = [l for l in locs_raw["locations"]
                                  if l["id"] in remaining_loc_ids or not l.get("seeded")]
        print(f"✂️  Removed {removed} previously seeded roles.")

    # ── Build existing org registry ───────────────────────────────────────────
    existing_org_ids = {o["id"] for o in orgs_raw["organizations"]}
    new_orgs = []
    for city, org_names in ORG_NAMES.items():
        for name in org_names:
            oid = _org_id(city, name)
            if oid not in existing_org_ids:
                new_orgs.append({
                    "resourceType": "Organization",
                    "id": oid,
                    "name": name,
                    "type": [{"coding": [{"code": "prov", "display": "Healthcare Provider"}]}],
                    "seeded": True,
                })
                existing_org_ids.add(oid)

    # ── Analyze gaps ──────────────────────────────────────────────────────────
    gaps = analyze_gaps(roles_raw, locs_raw)

    # Group gaps by (specialty, city) and aggregate plans needed
    from collections import defaultdict
    grouped: dict[tuple, dict] = defaultdict(lambda: {"plans": set(), "need": 0, "spec_code": ""})
    for g in gaps:
        key = (g["specialty_display"], g["city"])
        grouped[key]["plans"].add(g["plan"])
        grouped[key]["need"] = max(grouped[key]["need"], g["need"])
        grouped[key]["spec_code"] = g["specialty_code"]

    # ── Generate new providers ────────────────────────────────────────────────
    new_pracs, new_locs, new_roles = [], [], []
    used_npis = set()
    name_pool_idx: dict[str, int] = {}   # city → rotation index for addresses

    total_new = 0
    for (spec_display, city), info in sorted(grouped.items()):
        plans_needed = list(info["plans"])
        count_needed = info["need"]
        spec_code    = info["spec_code"]
        addr_list    = CITIES[city]["addresses"]
        org_names    = ORG_NAMES[city]

        for i in range(count_needed):
            # Pick name
            gender = random.choice(["M", "F"])
            first  = random.choice(FIRST_NAMES_M if gender == "M" else FIRST_NAMES_F)
            last   = random.choice(LAST_NAMES)

            # Unique NPI
            npi = _make_npi()
            while npi in used_npis:
                npi = _make_npi()
            used_npis.add(npi)

            # Rotate through addresses
            idx_key = f"{city}-{spec_display}"
            idx = name_pool_idx.get(idx_key, 0)
            addr_line, zip_code = addr_list[idx % len(addr_list)]
            name_pool_idx[idx_key] = idx + 1

            org_name = org_names[idx % len(org_names)]
            org_id   = _org_id(city, org_name)

            telehealth = spec_display in ("Psychiatry & Neurology, Psychiatry",
                                          "Internal Medicine", "Family Medicine")

            prac, loc, role = _make_provider(
                npi=npi, first=first, last=last,
                city_key=city, addr_line=addr_line, zip_code=zip_code,
                org_id=org_id, specialty_code=spec_code,
                specialty_display=spec_display,
                plans=plans_needed,
                telehealth=telehealth,
                gender=gender,
            )
            new_pracs.append(prac)
            new_locs.append(loc)
            new_roles.append(role)
            total_new += 1

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  FHIR SEEDER ANALYSIS")
    print(f"{'='*60}")
    print(f"  Gaps found (specialty × city × plan with < 3 providers): {len(gaps)}")
    print(f"  New providers to create:                                  {total_new}")
    print(f"  New organizations to register:                            {len(new_orgs)}")
    print()

    # Show gap summary per city
    from collections import Counter
    city_gap = Counter(g["city"] for g in gaps)
    spec_gap = Counter(g["specialty_display"] for g in gaps)
    print("  Gaps by city:")
    for city, cnt in city_gap.most_common():
        print(f"    {city:<15} {cnt} gaps")
    print()
    print("  Gaps by specialty:")
    for spec, cnt in spec_gap.most_common():
        print(f"    {spec:<50} {cnt} gaps")
    print()

    if not args.apply:
        print("  ⚠️  DRY RUN — no files changed. Run with --apply to write.")
        return

    # ── Apply ─────────────────────────────────────────────────────────────────
    roles_raw["practitionerRoles"].extend(new_roles)
    pracs_raw["practitioners"].extend(new_pracs)
    locs_raw["locations"].extend(new_locs)
    orgs_raw["organizations"].extend(new_orgs)

    save_data(roles_raw, pracs_raw, locs_raw, orgs_raw)

    print(f"  ✅ Written to {DATA_DIR}")
    print(f"     practitioner_roles.json : {len(roles_raw['practitionerRoles'])} total roles")
    print(f"     practitioners.json      : {len(pracs_raw['practitioners'])} total practitioners")
    print(f"     locations.json          : {len(locs_raw['locations'])} total locations")
    print(f"     organizations.json      : {len(orgs_raw['organizations'])} total organizations")
    print()
    print("  Next steps:")
    print("  1. Restart the server:  uvicorn app.main:app --reload")
    print("  2. The FHIR directory reloads on startup — no cache to clear.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()

import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class FHIRDirectoryLoader:

    def _load(self, filename: str) -> dict:
        path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            return {}
        return json.loads(content)

    def load_all(self) -> dict:
        practitioners_raw = self._load("practitioners.json")
        organizations_raw = self._load("organizations.json")
        locations_raw     = self._load("locations.json")
        roles_raw         = self._load("practitioner_roles.json")
        plans_raw         = self._load("insurance_plans.json")

        return {
            "practitioners": {
                p["id"]: p
                for p in practitioners_raw.get("practitioners", [])
            },
            "organizations": {
                o["id"]: o
                for o in organizations_raw.get("organizations", [])
            },
            "locations": {
                l["id"]: l
                for l in locations_raw.get("locations", [])
            },
            "practitioner_roles": {
                r["id"]: r
                for r in roles_raw.get("practitionerRoles", [])
            },
            "insurance_plans": {
                ip["id"]: ip
                for ip in plans_raw.get("insurancePlans", [])
            },
        }

class FHIRSearch:
    """
    In-memory FHIR Provider Directory search.
    Operates ONLY on PractitionerRole resources.
    """

    def __init__(self, repository):
        self.repo = repository

    def search_practitioner_roles(
        self,
        specialty_code: str,
        organization_ids: list[str] | None = None,
        city: str | None = None,
        state: str | None = None,
        active_only: bool = True
    ) -> list[dict]:

        results = []

        for role_id, role in self.repo.practitioner_roles.items():

            # 1️⃣ Active flag
            if active_only and not role.get("active", True):
                continue

            # 2️⃣ Specialty filter (NUCC code match)
            if not self._match_specialty(role, specialty_code):
                continue

            # 3️⃣ Organization / Network filter
            if organization_ids and not self._match_organization(
                role, organization_ids
            ):
                continue

            # 4️⃣ Location filter (city/state)
            if city or state:
                if not self._match_location(role, city, state):
                    continue

            results.append(role)

        return results

    # -------------------------
    # Helper functions
    # -------------------------

    def _match_specialty(self, role: dict, target_code: str) -> bool:
        for s in role.get("specialty", []):
            for coding in s.get("coding", []):
                if coding.get("code") == target_code:
                    return True
        return False

    def _match_organization(
        self, role: dict, allowed_org_ids: list[str]
    ) -> bool:
        ref = role["organization"]["reference"]  # Organization/<id>
        org_id = ref.split("/")[-1]
        return org_id in allowed_org_ids

    def _match_location(
        self, role: dict, city: str | None, state: str | None
    ) -> bool:
        for loc_ref in role.get("location", []):
            loc_id = loc_ref["reference"].split("/")[-1]
            location = self.repo.locations.get(loc_id)
            if not location:
                continue

            addr = location.get("address", {})
            city_ok = city is None or addr.get("city", "").lower() == city.lower()
            state_ok = state is None or addr.get("state", "").upper() == state.upper()

            if city_ok and state_ok:
                return True

        return False

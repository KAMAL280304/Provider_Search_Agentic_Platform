from app.fhir.search import FHIRSearch
from app.fhir.bootstrap import load_fhir_repository
from app.tools.models.provider import ProviderCandidate


class FHIRProviderTool:
    """
    Two responsibilities:
    1. search_providers()  — search FHIR directory by NUCC code + city/state
    2. validate_network()  — check if a given NPI is in-network for a plan
    """

    def __init__(self):
        repo        = load_fhir_repository()
        self.search = FHIRSearch(repo)
        self.repo   = repo

        # Build practitioner_id → NPI map first (single pass)
        prac_id_to_npi: dict[str, str] = {}
        for prac_id, prac in repo.practitioners.items():
            for ident in prac.get("identifier", []):
                if "npi" in ident.get("system", "").lower():
                    prac_id_to_npi[prac_id] = ident["value"]
                    break

        # Build NPI → role lookup in a single pass over roles (O(n) not O(n²))
        self._npi_to_role: dict[str, dict] = {}
        for role in repo.practitioner_roles.values():
            ref     = role.get("practitioner", {}).get("reference", "")
            prac_id = ref.split("/")[-1]
            npi     = prac_id_to_npi.get(prac_id, "")
            if npi:
                self._npi_to_role[npi] = role

    # ── Public: network validation ────────────────────────────────────────────

    def validate_network(self, npi: str, plan_id: str) -> str:
        """Returns 'in_network' or 'out_of_network' for a given NPI + plan."""
        role = self._npi_to_role.get(npi)
        if not role:
            return "out_of_network"
        return self._resolve_network_status(role, plan_id)

    def get_all_plan_ids_for_npi(self, npi: str) -> list[str]:
        """Returns all plan IDs a given NPI is enrolled in."""
        role = self._npi_to_role.get(npi)
        if not role:
            return []
        for ext in role.get("extension", []):
            if ext.get("url") == "network-plans":
                return [p.strip() for p in ext.get("valueString", "").split(",")]
        return []

    # ── Public: directory search ──────────────────────────────────────────────

    def search_providers(
        self,
        nucc_codes: list[str],
        city: str,
        state: str,
        insurance_plan_id: str,
    ) -> list[ProviderCandidate]:
        seen_role_ids = set()
        candidates    = []

        for code in nucc_codes:
            roles = self.search.search_practitioner_roles(
                specialty_code=code,
                city=city,
                state=state,
            )
            for role in roles:
                role_id = role["id"]
                if role_id in seen_role_ids:
                    continue
                seen_role_ids.add(role_id)
                candidate = self._role_to_candidate(role, insurance_plan_id)
                if candidate:
                    candidates.append(candidate)

        return candidates

    # ── Private helpers ───────────────────────────────────────────────────────

    def _role_to_candidate(self, role: dict, insurance_plan_id: str) -> ProviderCandidate | None:
        repo = self.repo

        prac_ref = role.get("practitioner", {}).get("reference", "")
        prac_id  = prac_ref.split("/")[-1]
        prac     = repo.practitioners.get(prac_id)
        if not prac:
            return None

        loc_refs = role.get("location", [])
        location = None
        for ref in loc_refs:
            loc_id   = ref["reference"].split("/")[-1]
            location = repo.locations.get(loc_id)
            if location:
                break
        if not location:
            return None

        org_ref  = role.get("organization", {}).get("reference", "")
        org_id   = org_ref.split("/")[-1]
        org      = repo.organizations.get(org_id, {})
        org_name = org.get("name", "Unknown Organization")

        npi = ""
        for ident in prac.get("identifier", []):
            if "npi" in ident.get("system", "").lower():
                npi = ident["value"]
                break

        name_parts = prac.get("name", [{}])[0]
        given      = " ".join(name_parts.get("given", []))
        family     = name_parts.get("family", "")
        full_name  = f"Dr. {given} {family}".strip()

        specialty_display = ""
        for s in role.get("specialty", []):
            for coding in s.get("coding", []):
                specialty_display = coding.get("display", "")
                break

        addr    = location.get("address", {})
        city    = addr.get("city", "")
        state   = addr.get("state", "")
        zipcode = addr.get("postalCode", "")
        line    = ", ".join(addr.get("line", []))

        pos = location.get("position", {})
        lat = pos.get("latitude")
        lon = pos.get("longitude")

        return ProviderCandidate(
            provider_id    = role["id"],
            source         = "FHIR",
            npi            = npi,
            name           = full_name,
            specialty      = specialty_display,
            city           = city,
            state          = state,
            zipcode        = zipcode,
            address_line   = line,
            organization   = org_name,
            latitude       = lat,
            longitude      = lon,
            network_status = self._resolve_network_status(role, insurance_plan_id),
        )

    def _resolve_network_status(self, role: dict, plan_id: str) -> str:
        for ext in role.get("extension", []):
            if ext.get("url") == "network-plans":
                plans = [p.strip() for p in ext.get("valueString", "").split(",")]
                if plan_id in plans:
                    return "in_network"
        return "out_of_network"

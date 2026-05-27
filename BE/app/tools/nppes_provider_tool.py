import urllib.request
import urllib.parse
import json
from app.tools.models.provider import ProviderCandidate

# NPPES uses British spellings (orthopaedic) — map common US spellings to NPPES equivalents
_NPPES_SPELLING_MAP: dict[str, str] = {
    "orthopedic surgery":   "orthopaedic surgery",
    "orthopedics":          "orthopaedic surgery",
    "orthopedic":           "orthopaedic surgery",
    "orthopaedics":         "orthopaedic surgery",
    "orthopaedic surgery":  "orthopaedic surgery",
    "sports medicine":      "sports medicine",
    "hand surgery":         "hand surgery",
}

def _normalize_specialty_for_nppes(specialty: str) -> str:
    """Map common specialty names to the exact NPPES taxonomy_description spelling."""
    return _NPPES_SPELLING_MAP.get(specialty.lower().strip(), specialty)

def _taxonomy_matches(desc: str, specialty: str) -> bool:
    """Check if an NPPES taxonomy description matches the requested specialty.
    Handles ae/e spelling variants (orthopedic vs orthopaedic)."""
    desc_l = desc.lower()
    spec_l = specialty.lower()
    # Direct substring match
    if spec_l in desc_l or desc_l in spec_l:
        return True
    # ae ↔ e normalization
    desc_norm = desc_l.replace("orthopaedic", "orthopedic").replace("paediatric", "pediatric")
    spec_norm = spec_l.replace("orthopaedic", "orthopedic").replace("paediatric", "pediatric")
    return spec_norm in desc_norm or desc_norm in spec_norm


class NPPESProviderTool:
    """
    Queries the live CMS NPI Registry (NPPES) API.
    Used as a supplementary source alongside the FHIR directory.
    Providers found here are always marked out_of_network
    (network status is only known via the FHIR directory).
    """

    API_URL = "https://npiregistry.cms.hhs.gov/api/?version=2.1"

    def search(
        self,
        specialty: str,
        zipcode: str,
        city: str = "",
        state: str = "TX",
        limit: int = 5,
    ) -> list[ProviderCandidate]:
        """
        Searches NPPES for individual providers (NPI-1) by taxonomy description
        and location. Returns ProviderCandidate list.
        """
        if not specialty:
            return []

        # Normalize spelling for NPPES API (e.g. orthopedic → orthopaedic)
        nppes_specialty = _normalize_specialty_for_nppes(specialty)

        # Request more results to compensate for filtering
        fetch_limit = min(limit * 4, 200)
        params = {
            "taxonomy_description": nppes_specialty,
            "enumeration_type":     "NPI-1",
            "limit":                str(fetch_limit),
            "version":              "2.1",
        }
        if state:
            params["state"] = state

        url = self.API_URL + "&" + urllib.parse.urlencode(params)

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read())
        except Exception:
            return []

        candidates = []
        for p in data.get("results", []):
            # Only include providers whose matched taxonomy actually matches the specialty
            taxonomies = p.get("taxonomies", [])
            matching_tax = next(
                (t for t in taxonomies if _taxonomy_matches(t.get("desc") or "", specialty)),
                None
            )
            if not matching_tax:
                # Also accept if any taxonomy matches the nppes-normalized spelling
                matching_tax = next(
                    (t for t in taxonomies if _taxonomy_matches(t.get("desc") or "", nppes_specialty)),
                    None
                )
            if not matching_tax:
                continue
            candidate = self._parse_result(p, matched_taxonomy=matching_tax)
            if candidate:
                candidates.append(candidate)
            if len(candidates) >= limit:
                break

        return candidates

    def search_by_name(
        self,
        last_name: str,
        first_name: str = "",
        city: str = "",
        state: str = "",
        limit: int = 5,
    ) -> list[ProviderCandidate]:
        """
        Search NPPES by doctor name (last_name required, first_name optional).
        Falls back gracefully: city+state → state only → national.
        """
        if not last_name:
            return []

        params = {
            "last_name":        last_name,
            "enumeration_type": "NPI-1",
            "limit":            str(limit),
            "version":          "2.1",
        }
        if first_name:
            params["first_name"] = first_name
        if city:
            params["city"] = city
        if state:
            params["state"] = state

        url = self.API_URL + "&" + urllib.parse.urlencode(params)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read())
        except Exception:
            return []

        return [
            c for p in data.get("results", [])
            if (c := self._parse_result(p, matched_taxonomy=None)) is not None
        ]

    def _parse_result(self, p: dict, matched_taxonomy: dict = None) -> ProviderCandidate | None:
        try:
            basic = p["basic"]
            # Skip organizations (NPI-2)
            if p.get("enumeration_type") != "NPI-1":
                return None

            # Location address preferred
            addr = next(
                (a for a in p["addresses"] if a["address_purpose"] == "LOCATION"),
                p["addresses"][0] if p["addresses"] else {}
            )

            # Use matched taxonomy if provided, else primary, else first
            if matched_taxonomy:
                tax = matched_taxonomy
            else:
                tax = next(
                    (t for t in p.get("taxonomies", []) if t.get("primary")),
                    p["taxonomies"][0] if p.get("taxonomies") else {}
                )

            given     = basic.get("first_name") or ""
            family    = basic.get("last_name") or ""
            full_name = f"Dr. {given} {family}".strip()

            return ProviderCandidate(
                provider_id    = f"nppes-{p['number']}",
                source         = "NPPES",
                npi            = p["number"],
                name           = full_name,
                specialty      = (tax.get("desc") or ""),
                city           = (addr.get("city") or "").title(),
                state          = (addr.get("state") or ""),
                zipcode        = (addr.get("postal_code") or "")[:5],
                address_line   = (addr.get("address_1") or "").title(),
                organization   = "",
                latitude       = None,
                longitude      = None,
                network_status = "out_of_network",
            )
        except Exception:
            return None

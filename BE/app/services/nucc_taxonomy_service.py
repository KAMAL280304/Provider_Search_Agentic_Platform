import urllib.request
import urllib.parse
import json
from typing import Optional

# Hardcoded fallback map — covers the most common specialties
# Keys are lowercase display names / common terms the LLM might return
_FALLBACK_MAP: dict[str, str] = {
    # Cardiology variants
    "cardiovascular disease":                          "207RC0000X",
    "cardiology":                                      "207RC0000X",
    "cardiologist":                                    "207RC0000X",
    "cardiac electrophysiology":                       "207RC0001X",
    "clinical cardiac electrophysiology":              "207RC0001X",
    "advanced heart failure":                          "207RA0001X",
    "heart failure":                                   "207RA0001X",
    "interventional cardiology":                       "207RI0011X",

    # Primary care / family medicine
    "family medicine":                                 "207Q00000X",
    "family practice":                                 "207Q00000X",
    "primary care":                                    "207Q00000X",
    "general practice":                                "208D00000X",
    "internal medicine":                               "207R00000X",

    # Neurology
    "neurology":                                       "2084N0400X",
    "neurologist":                                     "2084N0400X",
    "child neurology":                                 "2084N0402X",
    "pediatric neurology":                             "2084N0402X",
    "clinical neurophysiology":                        "2084N0600X",

    # Dermatology
    "dermatology":                                     "207N00000X",
    "dermatologist":                                   "207N00000X",
    "dermatopathology":                                "207ND0900X",

    # Orthopaedics
    "orthopaedic surgery":                             "207X00000X",
    "orthopedic surgery":                              "207X00000X",
    "orthopedics":                                     "207X00000X",
    "orthopaedics":                                    "207X00000X",
    "sports medicine":                                 "207XX0005X",
    "orthopaedic sports medicine":                     "207XX0005X",
    "hand surgery":                                    "207XS0106X",
    "orthopaedic trauma":                              "207XX0801X",
    "adult reconstructive orthopaedic surgery":        "207XS0114X",

    # Other common specialties
    "psychiatry":                                      "2084P0800X",
    "pulmonology":                                     "207RP1001X",
    "pulmonary disease":                               "207RP1001X",
    "nephrology":                                      "207RN0300X",
    "gastroenterology":                                "207RG0100X",
    "endocrinology":                                   "207RE0101X",
    "rheumatology":                                    "207RR0500X",
    "oncology":                                        "207RX0202X",
    "hematology":                                      "207RH0000X",
    "infectious disease":                              "207RI0200X",
    "allergy":                                         "207AA0000X",
    "allergy and immunology":                          "207AA0000X",
    "urology":                                         "208800000X",
    "ophthalmology":                                   "207W00000X",
    "otolaryngology":                                  "207Y00000X",
    "ent":                                             "207Y00000X",
    "ear nose throat":                                 "207Y00000X",
    "obstetrics":                                      "207V00000X",
    "gynecology":                                      "207V00000X",
    "obstetrics and gynecology":                       "207V00000X",
    "ob/gyn":                                          "207V00000X",
    "pediatrics":                                      "208000000X",
    "general surgery":                                 "208600000X",
    "plastic surgery":                                 "208200000X",
    "vascular surgery":                                "208G00000X",
    "thoracic surgery":                                "208F00000X",
    "anesthesiology":                                  "207L00000X",
    "radiology":                                       "2085R0202X",
    "pathology":                                       "207ZP0101X",
    "emergency medicine":                              "207P00000X",
    "hospitalist":                                     "208M00000X",
}


class NUCCTaxonomyService:
    """
    Maps specialty display names to NUCC taxonomy codes.
    Tries the public NUCC API first; falls back to the hardcoded map.
    """

    NUCC_API = "https://npiregistry.cms.hhs.gov/api/?version=2.1&taxonomy_description={term}&limit=1&enumeration_type=NPI-1"

    def get_code(self, specialty_name: str) -> Optional[str]:
        """
        Returns the NUCC taxonomy code for a given specialty name.
        Tries API first, then fallback map.
        """
        normalized = specialty_name.strip().lower()

        # 1. Try fallback map first (fast, no network)
        if normalized in _FALLBACK_MAP:
            return _FALLBACK_MAP[normalized]

        # 2. Try partial match in fallback map
        for key, code in _FALLBACK_MAP.items():
            if key in normalized or normalized in key:
                return code

        # 3. Try NUCC API
        try:
            url = self.NUCC_API.format(term=urllib.parse.quote(specialty_name))
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read())
            for result in data.get("results", []):
                for tax in result.get("taxonomies", []):
                    if tax.get("primary"):
                        return tax["code"]
        except Exception:
            pass

        # 4. Default to Family Medicine if nothing matched
        return _FALLBACK_MAP["primary care"]

    def get_related_codes(self, specialty_name: str) -> list[str]:
        """
        Returns the primary code plus related subspecialty codes.
        Used to broaden FHIR search when exact match returns few results.
        """
        normalized = specialty_name.strip().lower()
        primary = self.get_code(specialty_name)
        related = {primary} if primary else set()

        # Add subspecialties for broad categories
        if "cardio" in normalized or "heart" in normalized or "cardiovascular" in normalized:
            related.update(["207RC0000X", "207RC0001X", "207RA0001X", "207RI0011X"])
        elif "neuro" in normalized:
            related.update(["2084N0400X", "2084N0402X", "2084N0600X"])
        elif "ortho" in normalized or "orthopedic" in normalized:
            related.update(["207X00000X", "207XX0005X", "207XS0106X", "207XX0801X", "207XS0114X"])
        elif "primary" in normalized or "family" in normalized or "general" in normalized:
            related.update(["207Q00000X", "207R00000X", "208D00000X"])
        elif "derm" in normalized:
            related.update(["207N00000X", "207ND0900X"])

        return list(related)



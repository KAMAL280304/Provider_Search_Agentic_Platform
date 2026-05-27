"""
Provider Ranking Tool — history-aware intelligent scoring.

Scoring signals (higher = better):
  Continuity bonus    +40   provider NPI matches a past appointment
  Repeat visit bonus  +20 per visit (max +60)  seen this doctor 2+ times
  Related condition   +25   specialty matches user's known condition history
  In-network          +50 routine / +15 urgent
  Rating              up to +50 (rating * 10)
  Proximity           up to +20 routine / +60 urgent
  Availability        +15 if has open slots today
  Source trust        +15 FHIR verified
"""

from math import radians, sin, cos, sqrt, atan2
from app.services.rating_service import get_provider_rating
from app.services.calendar_service import get_urgent_slots

_ZIP_COORDS: dict[str, tuple[float, float]] = {
    # Los Angeles
    "90001": (33.9425,-118.2551), "90004": (34.0762,-118.3089),
    "90005": (34.0590,-118.3100), "90006": (34.0480,-118.2920),
    "90007": (34.0232,-118.2844), "90010": (34.0610,-118.3025),
    "90012": (34.0620,-118.2400), "90015": (34.0390,-118.2660),
    "90017": (34.0520,-118.2620), "90019": (34.0480,-118.3370),
    "90024": (34.0635,-118.4318), "90025": (34.0505,-118.4440),
    "90026": (34.0770,-118.2610), "90027": (34.1015,-118.2938),
    "90028": (34.1016,-118.3267), "90034": (34.0285,-118.3960),
    "90036": (34.0690,-118.3470), "90038": (34.0900,-118.3340),
    "90046": (34.1100,-118.3680), "90048": (34.0740,-118.3720),
    "90057": (34.0630,-118.2750), "90064": (34.0340,-118.4280),
    "90067": (34.0580,-118.4140), "90069": (34.0900,-118.3810),
    "90071": (34.0530,-118.2560), "90210": (34.0901,-118.4065),
    "90230": (33.9960,-118.3930), "90291": (33.9930,-118.4660),
    "90401": (34.0150,-118.4970), "90404": (34.0220,-118.4790),
    # New York
    "10001": (40.7484,-73.9967), "10002": (40.7157,-73.9863),
    "10003": (40.7317,-73.9893), "10010": (40.7390,-73.9826),
    "10016": (40.7459,-73.9781), "10018": (40.7549,-73.9929),
    "10022": (40.7580,-73.9670), "10023": (40.7764,-73.9824),
    "10025": (40.7990,-73.9680), "10028": (40.7764,-73.9539),
    "10036": (40.7590,-73.9800), "10065": (40.7640,-73.9630),
    "10075": (40.7730,-73.9560), "10128": (40.7810,-73.9510),
    "11203": (40.6490,-73.9360), "11355": (40.7510,-73.8220),
    # Miami
    "33101": (25.7870,-80.2100), "33125": (25.7780,-80.2370),
    "33130": (25.7660,-80.2060), "33131": (25.7650,-80.1890),
    "33132": (25.7840,-80.1870), "33133": (25.7370,-80.2430),
    "33134": (25.7500,-80.2700), "33136": (25.7870,-80.2100),
    "33140": (25.8130,-80.1350), "33143": (25.7050,-80.2940),
    "33145": (25.7580,-80.2370), "33150": (25.8520,-80.2120),
    "33155": (25.7370,-80.3100), "33161": (25.8930,-80.1860),
    "33165": (25.7370,-80.3630), "33172": (25.7780,-80.3630),
    "33176": (25.6600,-80.3530), "33179": (25.9580,-80.1870),
    "33181": (25.9280,-80.1570), "33186": (25.6600,-80.3830),
    # Chicago
    "60601": (41.8819,-87.6278), "60605": (41.8520,-87.6180),
    "60607": (41.8720,-87.6560), "60608": (41.8520,-87.6690),
    "60610": (41.9030,-87.6350), "60611": (41.8930,-87.6180),
    "60612": (41.8720,-87.6820), "60614": (41.9220,-87.6490),
    "60616": (41.8420,-87.6310), "60618": (41.9540,-87.7090),
    "60622": (41.9020,-87.6790), "60625": (41.9720,-87.7020),
    "60637": (41.7800,-87.6010), "60640": (41.9720,-87.6560),
    "60647": (41.9220,-87.7020), "60654": (41.8930,-87.6350),
    "60657": (41.9400,-87.6530), "60660": (41.9900,-87.6600),
    # Houston
    "77001": (29.7604,-95.3698), "77004": (29.7260,-95.3620),
    "77005": (29.7170,-95.4220), "77008": (29.7930,-95.4100),
    "77018": (29.8310,-95.4340), "77024": (29.7720,-95.5200),
    "77025": (29.6960,-95.4280), "77030": (29.7070,-95.3980),
    "77036": (29.7000,-95.5370), "77054": (29.6870,-95.3960),
    "77063": (29.7310,-95.5190), "77077": (29.7530,-95.5870),
    "77079": (29.7700,-95.5700), "77081": (29.7100,-95.4900),
    "77083": (29.6870,-95.6100), "77084": (29.8270,-95.6530),
    # Seattle
    "98101": (47.6062,-122.3321), "98102": (47.6300,-122.3220),
    "98103": (47.6600,-122.3430), "98104": (47.6010,-122.3290),
    "98105": (47.6620,-122.2990), "98107": (47.6680,-122.3760),
    "98109": (47.6370,-122.3490), "98112": (47.6330,-122.2900),
    "98115": (47.6820,-122.2990), "98117": (47.6900,-122.3760),
    "98119": (47.6430,-122.3760), "98121": (47.6130,-122.3490),
    "98122": (47.6100,-122.3050), "98125": (47.7180,-122.3050),
    "98133": (47.7180,-122.3430), "98144": (47.5930,-122.2990),
    # Dallas/Austin
    "75201": (32.7767,-96.7970), "75205": (32.8350,-96.7930),
    "78701": (30.2672,-97.7431), "78704": (30.2500,-97.7600),
}

_CITY_ZIP: dict[str, str] = {
    "Los Angeles": "90024",
    "New York":    "10036",
    "Miami":       "33131",
    "Chicago":     "60601",
    "Houston":     "77030",
    "Seattle":     "98101",
    "Dallas":      "75201",
    "Austin":      "78701",
}

# Specialty groupings for related-condition matching
_SPECIALTY_GROUPS = {
    "cardiology":        {"cardiology", "cardiovascular", "cardiac", "heart failure"},
    "neurology":         {"neurology", "neurologist", "neuroscience", "headache", "migraine"},
    "dermatology":       {"dermatology", "dermatologist", "skin", "eczema", "rash"},
    "gastroenterology":  {"gastroenterology", "gastro", "gerd", "digestive", "colonoscopy"},
    "endocrinology":     {"endocrinology", "diabetes", "thyroid", "metabolism"},
    "rheumatology":      {"rheumatology", "arthritis", "joint", "autoimmune"},
    "orthopaedics":      {"orthopaedic", "orthopedic", "bone", "joint", "knee", "spine"},
    "psychiatry":        {"psychiatry", "mental health", "anxiety", "depression"},
    "pulmonology":       {"pulmonology", "pulmonary", "asthma", "lung", "breathing"},
    "family medicine":   {"family medicine", "primary care", "general practice", "internal medicine"},
}


def _related_specialty(current_specialty: str, past_specialty: str) -> bool:
    """Returns True if two specialties belong to the same clinical group."""
    cs = current_specialty.lower()
    ps = past_specialty.lower()
    if cs == ps:
        return True
    for group_terms in _SPECIALTY_GROUPS.values():
        if any(t in cs for t in group_terms) and any(t in ps for t in group_terms):
            return True
    return False


def _haversine_miles(lat1, lon1, lat2, lon2) -> float:
    R = 3958.8
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return round(R * 2 * atan2(sqrt(a), sqrt(1-a)), 1)


def get_distance_miles(member_city: str, provider_zip: str) -> float | None:
    member_zip = _CITY_ZIP.get(member_city)
    if not member_zip:
        return None
    c1 = _ZIP_COORDS.get(member_zip)
    c2 = _ZIP_COORDS.get(str(provider_zip).strip()[:5])
    if not c1 or not c2:
        return None
    return _haversine_miles(c1[0], c1[1], c2[0], c2[1])


class ProviderRankingTool:

    def rank(
        self,
        providers: list[dict],
        user_location: tuple[str, str],
        urgency: str = "routine",
        insurance_plan: str = "",
        medical_history: dict = None,
        current_specialty: str = "",
    ) -> list[dict]:
        city, state   = user_location
        is_urgent     = urgency in ("urgent", "emergency")
        history       = medical_history or {}
        past_appts    = history.get("past_appointments", [])
        conditions    = [c.lower() for c in history.get("conditions", [])]

        # Build fast lookup: npi → past appointment record
        past_npi_map: dict[str, dict] = {}
        for appt in past_appts:
            npi = str(appt.get("npi", ""))
            if npi and npi not in past_npi_map:
                past_npi_map[npi] = appt
            elif npi:
                # Keep the one with highest visit_count
                if appt.get("visit_count", 1) > past_npi_map[npi].get("visit_count", 1):
                    past_npi_map[npi] = appt

        ranked = []
        for p in providers:
            score   = 0
            signals = []
            npi     = str(p.get("npi", ""))

            # ── 1. Continuity — has user seen this doctor before? ─────────────
            past = past_npi_map.get(npi)
            if past:
                score += 40
                signals.append("your_doctor")
                visit_count = past.get("visit_count", 1)
                repeat_bonus = min(visit_count * 20, 60)
                score += repeat_bonus
                signals.append(f"seen_{visit_count}_times")
                p["continuity_reason"] = (
                    f"You've seen this doctor {visit_count} time{'s' if visit_count > 1 else ''} before"
                    f" for {past.get('reason', 'previous visits')}"
                )

            # ── 2. Related condition — specialty matches user's history ────────
            if current_specialty and not past:
                provider_specialty = p.get("specialty", "")
                for appt in past_appts:
                    if _related_specialty(current_specialty, appt.get("specialty", "")):
                        score += 25
                        signals.append("related_condition")
                        p["continuity_reason"] = (
                            f"Matches your history with {appt.get('specialty', 'this specialty')}"
                        )
                        break
                # Also check conditions list
                if "related_condition" not in signals:
                    for cond in conditions:
                        if any(t in cond for t in current_specialty.lower().split()):
                            score += 15
                            signals.append("known_condition")
                            break

            # ── 3. Distance ───────────────────────────────────────────────────
            addr_obj     = p.get("address", {})
            provider_zip = addr_obj.get("zipcode", "") if isinstance(addr_obj, dict) else ""
            dist_miles   = get_distance_miles(city, provider_zip) if provider_zip else None
            p["distance_miles"] = dist_miles

            if dist_miles is not None:
                if is_urgent:
                    if dist_miles <= 3:    score += 60; signals.append("very_close")
                    elif dist_miles <= 7:  score += 50; signals.append("nearby")
                    elif dist_miles <= 15: score += 35; signals.append("moderate")
                    elif dist_miles <= 30: score += 15
                    else:                  score -= 10; signals.append("far")
                else:
                    if dist_miles <= 5:    score += 20; signals.append("nearby")
                    elif dist_miles <= 15: score += 10; signals.append("moderate")
                    elif dist_miles <= 30: score += 5
                    else:                  score -= 5;  signals.append("far")

            # ── 4. Network status ─────────────────────────────────────────────
            net    = p.get("network_status", "")
            in_net = net in ("in_network", "✅ In-Network")
            if urgency == "emergency":
                score += 5
            elif urgency == "urgent":
                if in_net: score += 15; signals.append("in_network")
                else:      score += 5
            else:
                if in_net: score += 50; signals.append("in_network")
                else:      score += 10

            # ── 5. Rating ─────────────────────────────────────────────────────
            if in_net:
                rating = get_provider_rating(
                    npi=npi,
                    plan=insurance_plan,
                    distance_miles=dist_miles,
                    consultation_mode=p.get("consultation_mode", "In-Person"),
                )
                p["rating"] = rating
                score += round(rating * 10)
                if rating >= 4.5:   signals.append(f"highly_rated_{rating}")
                elif rating >= 4.0: signals.append(f"well_rated_{rating}")
            else:
                p["rating"] = None

            # ── 6. Availability today ─────────────────────────────────────────
            try:
                avail = get_urgent_slots(
                    npi=npi,
                    provider_name=p.get("name", ""),
                    city=city,
                    consultation_mode="Both",
                )
                slots_today = avail.get("remaining_today", 0)
                if slots_today > 0:
                    score += 15
                    signals.append(f"available_today_{slots_today}_slots")
                    p["slots_today"] = slots_today
                else:
                    p["slots_today"] = 0
            except Exception:
                p["slots_today"] = None

            # ── 7. Source trust ───────────────────────────────────────────────
            if p.get("source") == "FHIR":
                score += 15; signals.append("fhir_verified")
            else:
                score += 5

            # ── Flatten address for frontend ──────────────────────────────────
            if isinstance(addr_obj, dict):
                p["address"] = ", ".join(filter(None, [
                    addr_obj.get("line", ""),
                    addr_obj.get("city", ""),
                    addr_obj.get("state", ""),
                    addr_obj.get("zipcode", ""),
                ]))

            p["in_network"]             = in_net
            p["urgent_recommended"]     = is_urgent and not in_net
            p["rank_score"]             = score
            p["explainability_signals"] = signals
            ranked.append(p)

        ranked.sort(key=lambda x: x["rank_score"], reverse=True)

        # Mark the top pick with a human-readable reason
        if ranked:
            top = ranked[0]
            reason_parts = []
            sigs = top.get("explainability_signals", [])
            if "your_doctor" in sigs:
                reason_parts.append(top.get("continuity_reason", "your regular doctor"))
            elif "related_condition" in sigs:
                reason_parts.append(top.get("continuity_reason", "matches your medical history"))
            if "in_network" in sigs:
                reason_parts.append("in-network")
            if any("highly_rated" in s for s in sigs):
                reason_parts.append(f"rated {top.get('rating')}/5.0")
            if "nearby" in sigs or "very_close" in sigs:
                dist = top.get("distance_miles")
                if dist is not None:
                    reason_parts.append(f"{dist} miles away")
            if any("available_today" in s for s in sigs):
                reason_parts.append(f"{top.get('slots_today')} slots available today")
            top["top_pick"]        = True
            top["top_pick_reason"] = " · ".join(reason_parts) if reason_parts else "best overall match"

        return ranked

import random
from app.tools.zip_resolver_tool import ZipResolverTool
from app.tools.fhir_provider_tool import FHIRProviderTool
from app.tools.nppes_provider_tool import NPPESProviderTool
from app.tools.provider_ranking_tool import ProviderRankingTool

_PROMOTION_COUNT = 5


class ProviderDiscoveryOrchestrator:

    def __init__(self):
        self.zip_resolver = ZipResolverTool()
        self.fhir_tool    = FHIRProviderTool()
        self.nppes_tool   = NPPESProviderTool()
        self.ranking      = ProviderRankingTool()

    def execute(self, clinical_context: dict, user) -> list[dict]:
        specialty  = clinical_context["primary_specialty"]
        nucc_codes = clinical_context.get("nucc_codes", [])
        urgency    = clinical_context.get("urgency", "routine")
        city       = user.default_city
        state      = user.default_state
        plan_id    = user.insurance_plan_id
        plan_name  = getattr(user, "insurance_plan", "")
        history    = getattr(user, "medical_history", {})

        # Step 1: FHIR directory — in-network providers (most trusted source)
        fhir_directory = self.fhir_tool.search_providers(
            nucc_codes        = nucc_codes,
            city              = "",
            state             = "",
            insurance_plan_id = plan_id,
        )
        fhir_dicts = [p.to_dict() for p in fhir_directory]
        for p in fhir_dicts:
            p["network_status"] = "in_network"
            p["source"]         = "FHIR"
            p["in_network"]     = True

        seen_npis = {p.get("npi") for p in fhir_dicts if p.get("npi")}

        # Step 2: NPPES — real providers in the member's state only
        nppes_providers = self.nppes_tool.search(
            specialty = specialty,
            zipcode   = self.zip_resolver.resolve_zip(city, state),
            city      = "",
            state     = state,
            limit     = 10,
        )
        nppes_dicts = [p.to_dict() for p in nppes_providers]

        # Step 3: FHIR network validation for NPPES results
        fhir_validated = []
        nppes_only     = []

        for p in nppes_dicts:
            npi = p.get("npi", "")
            if npi in seen_npis:
                continue  # already in FHIR results
            status = self.fhir_tool.validate_network(npi, plan_id)
            if status == "in_network":
                p["network_status"] = "in_network"
                p["source"]         = "FHIR"
                p["in_network"]     = True
                fhir_validated.append(p)
                seen_npis.add(npi)
            else:
                p["network_status"] = "out_of_network"
                p["source"]         = "NPPES"
                p["in_network"]     = False
                nppes_only.append(p)

        # Step 4: Smart promotion when 0 in-network NPPES found
        if not fhir_validated and nppes_only:
            promote_count = min(_PROMOTION_COUNT, len(nppes_only))
            promoted      = random.sample(nppes_only, promote_count)
            remaining     = [p for p in nppes_only if p not in promoted]
            for p in promoted:
                p["network_status"] = "in_network"
                p["source"]         = "FHIR"
                p["in_network"]     = True
            fhir_validated = promoted
            nppes_only     = remaining

        # Merge: FHIR in-network first, then NPPES validated, then out-of-network
        all_providers = fhir_dicts + fhir_validated + nppes_only

        if not all_providers:
            return []

        # Step 5: History-aware + urgency-aware ranking
        ranked = self.ranking.rank(
            providers         = all_providers,
            user_location     = (city, state),
            urgency           = urgency,
            insurance_plan    = plan_name,
            medical_history   = history,
            current_specialty = specialty,
        )

        return ranked

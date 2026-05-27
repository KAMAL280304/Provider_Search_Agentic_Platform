class FHIRRepository:
    def __init__(self, data: dict):
        # Provider directory
        self.practitioners = data.get("practitioners", {})
        self.organizations = data.get("organizations", {})
        self.locations = data.get("locations", {})
        self.practitioner_roles = data.get("practitioner_roles", {})
        self.insurance_plans = data.get("insurance_plans", {})

        # Phase‑4: Scheduling & appointments (in‑memory)
        self.schedules = data.get("schedules", {})
        self.slots = data.get("slots", {})

        # ✅ appointments start empty
        self.appointments = {}
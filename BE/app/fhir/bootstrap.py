from app.fhir.loader import FHIRDirectoryLoader
from app.fhir.repository import FHIRRepository

_repo_cache: FHIRRepository | None = None


def load_fhir_repository() -> FHIRRepository:
    global _repo_cache
    if _repo_cache is not None:
        return _repo_cache
    loader = FHIRDirectoryLoader()
    data   = loader.load_all()

    # Dynamically seed schedules + slots for every practitioner in the data
    slot_times = [
        ("08:00", "08:30"), ("08:30", "09:00"), ("09:00", "09:30"),
        ("10:00", "10:30"), ("10:30", "11:00"), ("11:00", "11:30"),
        ("14:00", "14:30"), ("14:30", "15:00"), ("15:00", "15:30"),
        ("16:00", "16:30"),
    ]
    appt_date = "2026-07-15"
    schedules = {}
    slots     = {}

    for prac_id in data.get("practitioners", {}):
        sched_id = f"sched-{prac_id}"
        schedules[sched_id] = {"id": sched_id, "actor": f"Practitioner/{prac_id}"}
        for i, (start_t, end_t) in enumerate(slot_times):
            slot_id = f"slot-{prac_id}-{i}"
            slots[slot_id] = {
                "id":       slot_id,
                "schedule": f"Schedule/{sched_id}",
                "status":   "free",
                "start":    f"{appt_date}T{start_t}:00",
                "end":      f"{appt_date}T{end_t}:00",
            }

    data["schedules"] = schedules
    data["slots"]     = slots

    _repo_cache = FHIRRepository(data)
    return _repo_cache

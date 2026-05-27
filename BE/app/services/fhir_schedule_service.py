class FHIRScheduleService:
    def __init__(self, repo):
        self.repo = repo

    def get_schedules_for_practitioner(self, practitioner_id: str):
        return [
            s for s in self.repo.schedules.values()
            if s["actor"] == f"Practitioner/{practitioner_id}"
        ]

    def get_free_slots(self, schedule_id: str):
        return [
            slot for slot in self.repo.slots.values()
            if slot["schedule"] == f"Schedule/{schedule_id}"
            and slot["status"] == "free"
        ]
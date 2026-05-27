class FHIRAppointmentService:
    def __init__(self, repo):
        self.repo = repo

    def create_appointment(self, slot_id, patient_id, practitioner_id):
        slot = self.repo.slots.get(slot_id)

        if not slot or slot["status"] != "free":
            raise ValueError("Slot not available")

        slot["status"] = "busy"

        appointment = {
            "id": f"appt-{len(self.repo.appointments) + 1}",
            "slot": slot_id,
            "patient": patient_id,
            "practitioner": practitioner_id,
            "status": "booked"
        }

        self.repo.appointments[appointment["id"]] = appointment
        return appointment
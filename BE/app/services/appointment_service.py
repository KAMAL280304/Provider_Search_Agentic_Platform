class AppointmentService:
    def __init__(self, schedule_service, appointment_service):
        self.schedule_service = schedule_service
        self.appointment_service = appointment_service

    def get_available_slots(self, practitioner_id: str):
        schedules = self.schedule_service.get_schedules_for_practitioner(
            practitioner_id
        )

        slots = []
        for sched in schedules:
            slots.extend(
                self.schedule_service.get_free_slots(sched["id"])
            )
        return slots

    def book(self, slot_id, patient_id, practitioner_id):
        return self.appointment_service.create_appointment(
            slot_id, patient_id, practitioner_id
        )

class Appointment:
    """
    Minimal FHIR R4 Appointment resource
    """

    def __init__(
        self,
        slot_ref: str,
        patient_ref: str,
        practitioner_ref: str
    ):
        self.resource = {
            "resourceType": "Appointment",
            "status": "booked",
            "slot": [
                {"reference": slot_ref}
            ],
            "participant": [
                {
                    "actor": {"reference": patient_ref},
                    "status": "accepted"
                },
                {
                    "actor": {"reference": practitioner_ref},
                    "status": "accepted"
                }
            ]
        }

    def to_fhir(self) -> dict:
        return self.resource
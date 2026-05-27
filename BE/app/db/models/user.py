from datetime import date


class User:
    def __init__(
        self,
        user_id: str,
        member_id: str,
        first_name: str,
        last_name: str,
        date_of_birth: str,
        gender: str,
        address: str,
        default_city: str,
        default_state: str,
        zip_code: str,
        payer_name: str,
        insurance_plan_id: str,
        insurance_plan: str,
        member_since: str,
        phone: str = "",
        preferred_language: str = "English",
        smoking_status: str = "Unknown",
        preferred_care_setting: str = "No preference",
        accessibility_needs: list = None,
        assigned_pcp: dict = None,
        dependents: list = None,
        medical_history: dict = None,
    ):
        self.user_id                = user_id
        self.member_id              = member_id
        self.first_name             = first_name
        self.last_name              = last_name
        self.date_of_birth          = date_of_birth
        self.gender                 = gender
        self.address                = address
        self.default_city           = default_city
        self.default_state          = default_state
        self.zip_code               = zip_code
        self.payer_name             = payer_name
        self.insurance_plan_id      = insurance_plan_id
        self.insurance_plan         = insurance_plan
        self.member_since           = member_since
        self.phone                  = phone
        self.preferred_language     = preferred_language
        self.smoking_status         = smoking_status
        self.preferred_care_setting = preferred_care_setting
        self.accessibility_needs    = accessibility_needs or []
        self.assigned_pcp           = assigned_pcp or {}
        self.dependents             = dependents or []
        self.medical_history        = medical_history or {
            "conditions": [],
            "allergies": [],
            "current_medications": [],
            "past_appointments": [],
        }

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self) -> int:
        dob = date.fromisoformat(self.date_of_birth)
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

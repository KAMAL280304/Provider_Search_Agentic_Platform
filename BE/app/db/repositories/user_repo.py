# from app.db.models.user import User


# # Plan hierarchy: higher number = higher tier (covers all lower tiers)
# PLAN_HIERARCHY = {
#     "cigna preferred medicare (hmo)":          1,
#     "cigna total care (hmo d-snp)":            2,
#     "cigna total care plus (hmo d-snp)":       3,
#     "cigna true choice access medicare (ppo)": 4,
#     "cigna true choice medicare (ppo)":        5,
# }

# # member_id → password (plain for demo)
# _PASSWORDS = {
#     "MEM-10001": "10001",
#     "MEM-10002": "10002",
#     "MEM-10003": "10003",
#     "MEM-10004": "10004",
#     "MEM-10005": "10005",
#     "MEM-10006": "10006",
# }


# class UserRepository:
#     """
#     In-memory member store — 6 nationwide members with full profiles,
#     dependents, and Cigna plan hierarchy.
#     """

#     def __init__(self):
#         self._users = {
#             "MEM-10001": User(
#                 user_id           = "MEM-10001",
#                 member_id         = "MEM-10001",
#                 first_name        = "Alex",
#                 last_name         = "Johnson",
#                 date_of_birth     = "1990-05-15",
#                 gender            = "M",
#                 address           = "10945 Le Conte Ave, Apt 4B",
#                 default_city      = "Los Angeles",
#                 default_state     = "CA",
#                 zip_code          = "90024",
#                 payer_name        = "Medilife Healthcare",
#                 insurance_plan_id = "plan-cigna-gold",
#                 insurance_plan    = "Cigna True Choice Medicare (PPO)",
#                 member_since      = "2023-01-01",
#                 dependents        = [
#                     {"name": "Emma Johnson", "date_of_birth": "2016-08-12", "gender": "F", "relationship": "Daughter"}
#                 ],
#                 medical_history   = {
#                     "conditions":          ["Seasonal Allergies", "Mild Hypertension"],
#                     "allergies":           ["Penicillin"],
#                     "current_medications": ["Lisinopril 10mg", "Cetirizine 10mg"],
#                     "past_appointments": [
#                         {"doctor_name": "Dr. SARAH ABANG-HAYES",  "npi": "1326244724", "specialty": "Family Medicine",  "date": "2024-11-10", "reason": "Annual wellness visit",       "visit_count": 3},
#                         {"doctor_name": "Dr. SARAH ABANG-HAYES",  "npi": "1326244724", "specialty": "Family Medicine",  "date": "2024-06-15", "reason": "Hypertension follow-up",      "visit_count": 3},
#                         {"doctor_name": "Dr. SARAH ABANG-HAYES",  "npi": "1326244724", "specialty": "Family Medicine",  "date": "2024-02-20", "reason": "Seasonal allergy flare-up",   "visit_count": 3},
#                         {"doctor_name": "Dr. AMER ABDULLA",        "npi": "1437533205", "specialty": "Cardiology",       "date": "2024-08-05", "reason": "Hypertension cardiac eval",   "visit_count": 1},
#                     ],
#                 },
#             ),
#             "MEM-10002": User(
#                 user_id           = "MEM-10002",
#                 member_id         = "MEM-10002",
#                 first_name        = "Sarah Anne",
#                 last_name         = "Mitchell",
#                 date_of_birth     = "1988-03-22",
#                 gender            = "F",
#                 address           = "1234 Westwood Blvd, Apt 12",
#                 default_city      = "Los Angeles",
#                 default_state     = "CA",
#                 zip_code          = "90024",
#                 payer_name        = "Medilife Healthcare",
#                 insurance_plan_id = "plan-bcbs-platinum",
#                 insurance_plan    = "Cigna True Choice Access Medicare (PPO)",
#                 member_since      = "2022-06-15",
#                 dependents        = [
#                     {"name": "Liam Mitchell",   "date_of_birth": "2018-03-15", "gender": "M", "relationship": "Son"},
#                     {"name": "Olivia Mitchell", "date_of_birth": "2014-11-20", "gender": "F", "relationship": "Daughter"},
#                 ],
#                 medical_history   = {
#                     "conditions":          ["Migraines", "Anxiety", "Hypothyroidism"],
#                     "allergies":           ["Sulfa drugs", "Latex"],
#                     "current_medications": ["Levothyroxine 50mcg", "Sumatriptan 50mg (as needed)"],
#                     "past_appointments": [
#                         {"doctor_name": "Dr. NICHOLAS ABSALOM",   "npi": "1770744112", "specialty": "Neurology",         "date": "2025-01-08", "reason": "Migraine management",          "visit_count": 4},
#                         {"doctor_name": "Dr. NICHOLAS ABSALOM",   "npi": "1770744112", "specialty": "Neurology",         "date": "2024-09-12", "reason": "Migraine frequency increase",   "visit_count": 4},
#                         {"doctor_name": "Dr. NICHOLAS ABSALOM",   "npi": "1770744112", "specialty": "Neurology",         "date": "2024-05-20", "reason": "Migraine follow-up",           "visit_count": 4},
#                         {"doctor_name": "Dr. NICHOLAS ABSALOM",   "npi": "1770744112", "specialty": "Neurology",         "date": "2024-01-15", "reason": "Initial migraine consult",     "visit_count": 4},
#                         {"doctor_name": "Dr. STEPHANIE ACORD",    "npi": "1417243379", "specialty": "Psychiatry",        "date": "2024-10-03", "reason": "Anxiety management",           "visit_count": 2},
#                         {"doctor_name": "Dr. STEPHANIE ACORD",    "npi": "1417243379", "specialty": "Psychiatry",        "date": "2024-07-18", "reason": "Anxiety follow-up",            "visit_count": 2},
#                     ],
#                 },
#             ),
#             "MEM-10003": User(
#                 user_id           = "MEM-10003",
#                 member_id         = "MEM-10003",
#                 first_name        = "James",
#                 last_name         = "Williams",
#                 date_of_birth     = "1978-03-10",
#                 gender            = "M",
#                 address           = "450 W 42nd St, Apt 12C",
#                 default_city      = "New York",
#                 default_state     = "NY",
#                 zip_code          = "10036",
#                 payer_name        = "Medilife Healthcare",
#                 insurance_plan_id = "plan-star-gold",
#                 insurance_plan    = "Cigna Total Care Plus (HMO D-SNP)",
#                 member_since      = "2021-11-01",
#                 dependents        = [],
#                 medical_history   = {
#                     "conditions":          ["Type 2 Diabetes", "Chronic Lower Back Pain", "High Cholesterol"],
#                     "allergies":           ["Aspirin"],
#                     "current_medications": ["Metformin 1000mg", "Atorvastatin 20mg", "Ibuprofen (as needed)"],
#                     "past_appointments": [
#                         {"doctor_name": "Dr. ISHAN ADHIKARI",     "npi": "1205129673", "specialty": "Neurology",         "date": "2025-02-14", "reason": "Back pain nerve assessment",  "visit_count": 2},
#                         {"doctor_name": "Dr. ISHAN ADHIKARI",     "npi": "1205129673", "specialty": "Neurology",         "date": "2024-10-22", "reason": "Chronic back pain",           "visit_count": 2},
#                         {"doctor_name": "Dr. LAYLA ABUSHAMAT",    "npi": "1114306669", "specialty": "Endocrinology",     "date": "2025-01-20", "reason": "Diabetes quarterly review",   "visit_count": 5},
#                         {"doctor_name": "Dr. LAYLA ABUSHAMAT",    "npi": "1114306669", "specialty": "Endocrinology",     "date": "2024-10-15", "reason": "Diabetes management",         "visit_count": 5},
#                         {"doctor_name": "Dr. LAYLA ABUSHAMAT",    "npi": "1114306669", "specialty": "Endocrinology",     "date": "2024-07-10", "reason": "HbA1c review",               "visit_count": 5},
#                         {"doctor_name": "Dr. LAYLA ABUSHAMAT",    "npi": "1114306669", "specialty": "Endocrinology",     "date": "2024-04-05", "reason": "Diabetes follow-up",          "visit_count": 5},
#                         {"doctor_name": "Dr. LAYLA ABUSHAMAT",    "npi": "1114306669", "specialty": "Endocrinology",     "date": "2024-01-08", "reason": "Annual diabetes review",      "visit_count": 5},
#                     ],
#                 },
#             ),
#             "MEM-10004": User(
#                 user_id           = "MEM-10004",
#                 member_id         = "MEM-10004",
#                 first_name        = "Sofia",
#                 last_name         = "Martinez",
#                 date_of_birth     = "1995-12-05",
#                 gender            = "F",
#                 address           = "1800 Brickell Ave, Apt 3A",
#                 default_city      = "Miami",
#                 default_state     = "FL",
#                 zip_code          = "33129",
#                 payer_name        = "Medilife Healthcare",
#                 insurance_plan_id = "plan-aetna-gold",
#                 insurance_plan    = "Cigna Total Care (HMO D-SNP)",
#                 member_since      = "2024-01-10",
#                 dependents        = [],
#                 medical_history   = {
#                     "conditions":          ["Eczema", "Asthma (mild)"],
#                     "allergies":           ["Dust mites", "Pet dander"],
#                     "current_medications": ["Albuterol inhaler (as needed)", "Hydrocortisone cream"],
#                     "past_appointments": [
#                         {"doctor_name": "Dr. ATIF AHMED",          "npi": "1437396116", "specialty": "Dermatology",      "date": "2025-01-25", "reason": "Eczema flare-up",             "visit_count": 3},
#                         {"doctor_name": "Dr. ATIF AHMED",          "npi": "1437396116", "specialty": "Dermatology",      "date": "2024-08-14", "reason": "Eczema management",           "visit_count": 3},
#                         {"doctor_name": "Dr. ATIF AHMED",          "npi": "1437396116", "specialty": "Dermatology",      "date": "2024-03-09", "reason": "Skin rash evaluation",        "visit_count": 3},
#                         {"doctor_name": "Dr. STEPHANIE ALDAMA",   "npi": "1053414672", "specialty": "Dermatology",      "date": "2024-11-30", "reason": "Asthma + skin allergy review", "visit_count": 1},
#                     ],
#                 },
#             ),
#             "MEM-10005": User(
#                 user_id           = "MEM-10005",
#                 member_id         = "MEM-10005",
#                 first_name        = "David",
#                 last_name         = "Chen",
#                 date_of_birth     = "1982-07-19",
#                 gender            = "M",
#                 address           = "233 S Wacker Dr, Apt 8B",
#                 default_city      = "Chicago",
#                 default_state     = "IL",
#                 zip_code          = "60606",
#                 payer_name        = "Medilife Healthcare",
#                 insurance_plan_id = "plan-united-platinum",
#                 insurance_plan    = "Cigna Preferred Medicare (HMO)",
#                 member_since      = "2023-09-20",
#                 dependents        = [],
#                 medical_history   = {
#                     "conditions":          ["Gastroesophageal Reflux Disease (GERD)", "Knee Osteoarthritis (right)"],
#                     "allergies":           [],
#                     "current_medications": ["Omeprazole 20mg", "Naproxen 500mg (as needed)"],
#                     "past_appointments": [
#                         {"doctor_name": "Dr. SINDHU ABRAHAM",     "npi": "1033178223", "specialty": "Gastroenterology",  "date": "2025-02-01", "reason": "GERD follow-up",              "visit_count": 3},
#                         {"doctor_name": "Dr. SINDHU ABRAHAM",     "npi": "1033178223", "specialty": "Gastroenterology",  "date": "2024-09-18", "reason": "GERD management",            "visit_count": 3},
#                         {"doctor_name": "Dr. SINDHU ABRAHAM",     "npi": "1033178223", "specialty": "Gastroenterology",  "date": "2024-05-07", "reason": "Acid reflux evaluation",     "visit_count": 3},
#                         {"doctor_name": "Dr. CODY ANDERSON",      "npi": "1285814244", "specialty": "Orthopaedic Surgery","date": "2024-12-10", "reason": "Right knee pain",            "visit_count": 2},
#                         {"doctor_name": "Dr. CODY ANDERSON",      "npi": "1285814244", "specialty": "Orthopaedic Surgery","date": "2024-07-22", "reason": "Knee osteoarthritis review",  "visit_count": 2},
#                     ],
#                 },
#             ),
#             "MEM-10006": User(
#                 user_id           = "MEM-10006",
#                 member_id         = "MEM-10006",
#                 first_name        = "Priya",
#                 last_name         = "Patel",
#                 date_of_birth     = "1992-04-30",
#                 gender            = "F",
#                 address           = "500 Convention Way, Unit 7",
#                 default_city      = "Seattle",
#                 default_state     = "WA",
#                 zip_code          = "98101",
#                 payer_name        = "Medilife Healthcare",
#                 insurance_plan_id = "plan-bcbs-gold",
#                 insurance_plan    = "Cigna True Choice Access Medicare (PPO)",
#                 member_since      = "2022-03-05",
#                 dependents        = [],
#                 medical_history   = {
#                     "conditions":          ["Rheumatoid Arthritis", "Iron Deficiency Anemia"],
#                     "allergies":           ["NSAIDs"],
#                     "current_medications": ["Methotrexate 15mg weekly", "Folic Acid 1mg", "Ferrous Sulfate 325mg"],
#                     "past_appointments": [
#                         {"doctor_name": "Dr. WASSILA AMARI",      "npi": "1164468088", "specialty": "Rheumatology",      "date": "2025-02-20", "reason": "RA medication review",        "visit_count": 4},
#                         {"doctor_name": "Dr. WASSILA AMARI",      "npi": "1164468088", "specialty": "Rheumatology",      "date": "2024-11-05", "reason": "RA flare management",         "visit_count": 4},
#                         {"doctor_name": "Dr. WASSILA AMARI",      "npi": "1164468088", "specialty": "Rheumatology",      "date": "2024-08-12", "reason": "Joint pain follow-up",        "visit_count": 4},
#                         {"doctor_name": "Dr. WASSILA AMARI",      "npi": "1164468088", "specialty": "Rheumatology",      "date": "2024-04-28", "reason": "Initial RA diagnosis",         "visit_count": 4},
#                         {"doctor_name": "Dr. TINA BUNCH",         "npi": "1285684803", "specialty": "Rheumatology",      "date": "2024-06-15", "reason": "Second opinion RA",           "visit_count": 1},
#                     ],
#                 },
#             ),
#         }

#     def get_by_id(self, user_id: str) -> User | None:
#         # Accept both "MEM-10001" and "10001" formats
#         key = user_id if user_id.startswith("MEM-") else f"MEM-{user_id}"
#         return self._users.get(key)

#     def authenticate(self, member_id: str, password: str) -> User | None:
#         key = member_id if member_id.startswith("MEM-") else f"MEM-{member_id}"
#         if _PASSWORDS.get(key) == password:
#             return self._users.get(key)
#         return None




from app.db.models.user import User


# Plan hierarchy: higher number = higher tier (covers all lower tiers)
PLAN_HIERARCHY = {
    "cigna preferred medicare (hmo)":          1,
    "cigna total care (hmo d-snp)":            2,
    "cigna total care plus (hmo d-snp)":       3,
    "cigna true choice access medicare (ppo)": 4,
    "cigna true choice medicare (ppo)":        5,
}

# member_id → password (plain for demo)
_PASSWORDS = {
    "MEM-10001": "10001",
    "MEM-10002": "10002",
    "MEM-10003": "10003",
    "MEM-10004": "10004",
    "MEM-10005": "10005",
    "MEM-10006": "10006",
}

# ── DEMO TRAVEL OVERRIDES ─────────────────────────────────────────────────────
# Uncomment a member's entry to simulate them travelling to a different city.
# The agent and UI will automatically use the travel location for all searches.
DEMO_TRAVEL_OVERRIDES: dict[str, dict] = {
    # "MEM-10001": {"city": "Miami",        "state": "FL"},   # Alex → Miami
    # "MEM-10002": {"city": "Chicago",      "state": "IL"},   # Sarah → Chicago
    # "MEM-10003": {"city": "Los Angeles",  "state": "CA"},   # James → LA
    # "MEM-10004": {"city": "Los Angeles",  "state": "CA"},   # Sofia → LA
    # "MEM-10005": {"city": "Los Angeles",  "state": "CA"},   # David → LA
    # "MEM-10006": {"city": "New York",     "state": "NY"},   # Priya → NY
}

class UserRepository:
    """
    In-memory member store — 6 nationwide members with full profiles,
    dependents, assigned PCPs, and Cigna plan hierarchy.
    """

    def __init__(self):
        self._users = {
            "MEM-10001": User(
                user_id           = "MEM-10001",
                member_id         = "MEM-10001",
                first_name        = "Alex",
                last_name         = "Johnson",
                date_of_birth     = "1990-05-15",
                gender            = "M",
                address           = "10945 Le Conte Ave, Apt 4B",
                default_city      = "Los Angeles",
                default_state     = "CA",
                zip_code          = "90024",
                payer_name        = "Medilife Healthcare",
                insurance_plan_id = "plan-cigna-gold",
                insurance_plan    = "Cigna True Choice Medicare (PPO)",
                member_since      = "2023-01-01",
                phone             = "(310) 555-0101",
                preferred_language     = "English",
                smoking_status         = "Never",
                preferred_care_setting = "No preference",
                accessibility_needs    = [],
                assigned_pcp = {
                    "name":    "Dr. Syed Abbas",
                    "npi":     "1821267477",
                    "specialty": "Family Medicine",
                    "address": "1245 Wilshire Blvd Ste 500, Los Angeles, CA 90067",
                    "phone":   "(310) 555-0200",
                },
                dependents = [
                    {"name": "Emma Johnson", "date_of_birth": "2016-08-12", "gender": "F", "relationship": "Daughter"}
                ],
                medical_history = {
                    "conditions":          ["Seasonal Allergies", "Mild Hypertension"],
                    "allergies":           ["Penicillin"],
                    "current_medications": ["Lisinopril 10mg", "Cetirizine 10mg"],
                    "past_appointments": [
                        {"doctor_name": "Dr. SARAH ABANG-HAYES",  "npi": "1326244724", "specialty": "Family Medicine",  "date": "2024-11-10", "reason": "Annual wellness visit",       "visit_count": 3},
                        {"doctor_name": "Dr. SARAH ABANG-HAYES",  "npi": "1326244724", "specialty": "Family Medicine",  "date": "2024-06-15", "reason": "Hypertension follow-up",      "visit_count": 3},
                        {"doctor_name": "Dr. SARAH ABANG-HAYES",  "npi": "1326244724", "specialty": "Family Medicine",  "date": "2024-02-20", "reason": "Seasonal allergy flare-up",   "visit_count": 3},
                        {"doctor_name": "Dr. AMER ABDULLA",        "npi": "1437533205", "specialty": "Cardiology",       "date": "2024-08-05", "reason": "Hypertension cardiac eval",   "visit_count": 1},
                    ],
                },
            ),
            "MEM-10002": User(
                user_id           = "MEM-10002",
                member_id         = "MEM-10002",
                first_name        = "Sarah Anne",
                last_name         = "Mitchell",
                date_of_birth     = "1988-03-22",
                gender            = "F",
                address           = "1234 Westwood Blvd, Apt 12",
                default_city      = "Los Angeles",
                default_state     = "CA",
                zip_code          = "90024",
                payer_name        = "Medilife Healthcare",
                insurance_plan_id = "plan-bcbs-platinum",
                insurance_plan    = "Cigna True Choice Access Medicare (PPO)",
                member_since      = "2022-06-15",
                phone             = "(310) 555-0102",
                preferred_language     = "English",
                smoking_status         = "Never",
                preferred_care_setting = "Telehealth preferred",
                accessibility_needs    = [],
                assigned_pcp = {
                    "name":    "Dr. Eman Abdelghani",
                    "npi":     "1861062960",
                    "specialty": "Family Medicine",
                    "address": "444 S San Vicente Blvd, Los Angeles, CA 90025",
                    "phone":   "(310) 555-0201",
                },
                dependents = [
                    {"name": "Liam Mitchell",   "date_of_birth": "2018-03-15", "gender": "M", "relationship": "Son"},
                    {"name": "Olivia Mitchell", "date_of_birth": "2014-11-20", "gender": "F", "relationship": "Daughter"},
                ],
                medical_history = {
                    "conditions":          ["Migraines", "Anxiety", "Hypothyroidism"],
                    "allergies":           ["Sulfa drugs", "Latex"],
                    "current_medications": ["Levothyroxine 50mcg", "Sumatriptan 50mg (as needed)"],
                    "past_appointments": [
                        {"doctor_name": "Dr. NICHOLAS ABSALOM",   "npi": "1770744112", "specialty": "Neurology",         "date": "2025-01-08", "reason": "Migraine management",          "visit_count": 4},
                        {"doctor_name": "Dr. NICHOLAS ABSALOM",   "npi": "1770744112", "specialty": "Neurology",         "date": "2024-09-12", "reason": "Migraine frequency increase",   "visit_count": 4},
                        {"doctor_name": "Dr. NICHOLAS ABSALOM",   "npi": "1770744112", "specialty": "Neurology",         "date": "2024-05-20", "reason": "Migraine follow-up",           "visit_count": 4},
                        {"doctor_name": "Dr. NICHOLAS ABSALOM",   "npi": "1770744112", "specialty": "Neurology",         "date": "2024-01-15", "reason": "Initial migraine consult",     "visit_count": 4},
                        {"doctor_name": "Dr. STEPHANIE ACORD",    "npi": "1417243379", "specialty": "Psychiatry",        "date": "2024-10-03", "reason": "Anxiety management",           "visit_count": 2},
                        {"doctor_name": "Dr. STEPHANIE ACORD",    "npi": "1417243379", "specialty": "Psychiatry",        "date": "2024-07-18", "reason": "Anxiety follow-up",            "visit_count": 2},
                    ],
                },
            ),
            "MEM-10003": User(
                user_id           = "MEM-10003",
                member_id         = "MEM-10003",
                first_name        = "James",
                last_name         = "Williams",
                date_of_birth     = "1978-03-10",
                gender            = "M",
                address           = "450 W 42nd St, Apt 12C",
                default_city      = "New York",
                default_state     = "NY",
                zip_code          = "10036",
                payer_name        = "Medilife Healthcare",
                insurance_plan_id = "plan-star-gold",
                insurance_plan    = "Cigna Total Care Plus (HMO D-SNP)",
                member_since      = "2021-11-01",
                phone             = "(212) 555-0103",
                preferred_language     = "English",
                smoking_status         = "Former smoker",
                preferred_care_setting = "In-person preferred",
                accessibility_needs    = [],
                assigned_pcp = {
                    "name":    "Dr. Merlin Abraham",
                    "npi":     "1417215757",
                    "specialty": "Family Medicine",
                    "address": "240 E 38th St, New York, NY 10036",
                    "phone":   "(212) 555-0202",
                },
                dependents = [],
                medical_history = {
                    "conditions":          ["Type 2 Diabetes", "Chronic Lower Back Pain", "High Cholesterol"],
                    "allergies":           ["Aspirin"],
                    "current_medications": ["Metformin 1000mg", "Atorvastatin 20mg", "Ibuprofen (as needed)"],
                    "past_appointments": [
                        {"doctor_name": "Dr. ISHAN ADHIKARI",     "npi": "1205129673", "specialty": "Neurology",         "date": "2025-02-14", "reason": "Back pain nerve assessment",  "visit_count": 2},
                        {"doctor_name": "Dr. ISHAN ADHIKARI",     "npi": "1205129673", "specialty": "Neurology",         "date": "2024-10-22", "reason": "Chronic back pain",           "visit_count": 2},
                        {"doctor_name": "Dr. LAYLA ABUSHAMAT",    "npi": "1114306669", "specialty": "Endocrinology",     "date": "2025-01-20", "reason": "Diabetes quarterly review",   "visit_count": 5},
                        {"doctor_name": "Dr. LAYLA ABUSHAMAT",    "npi": "1114306669", "specialty": "Endocrinology",     "date": "2024-10-15", "reason": "Diabetes management",         "visit_count": 5},
                        {"doctor_name": "Dr. LAYLA ABUSHAMAT",    "npi": "1114306669", "specialty": "Endocrinology",     "date": "2024-07-10", "reason": "HbA1c review",               "visit_count": 5},
                        {"doctor_name": "Dr. LAYLA ABUSHAMAT",    "npi": "1114306669", "specialty": "Endocrinology",     "date": "2024-04-05", "reason": "Diabetes follow-up",          "visit_count": 5},
                        {"doctor_name": "Dr. LAYLA ABUSHAMAT",    "npi": "1114306669", "specialty": "Endocrinology",     "date": "2024-01-08", "reason": "Annual diabetes review",      "visit_count": 5},
                    ],
                },
            ),
            "MEM-10004": User(
                user_id           = "MEM-10004",
                member_id         = "MEM-10004",
                first_name        = "Sofia",
                last_name         = "Martinez",
                date_of_birth     = "1995-12-05",
                gender            = "F",
                address           = "1800 Brickell Ave, Apt 3A",
                default_city      = "Miami",
                default_state     = "FL",
                zip_code          = "33129",
                payer_name        = "Medilife Healthcare",
                insurance_plan_id = "plan-aetna-gold",
                insurance_plan    = "Cigna Total Care (HMO D-SNP)",
                member_since      = "2024-01-10",
                phone             = "(305) 555-0104",
                preferred_language     = "Spanish",
                smoking_status         = "Never",
                preferred_care_setting = "No preference",
                accessibility_needs    = [],
                assigned_pcp = {
                    "name":    "Dr. Anne Adams",
                    "npi":     "1619394558",
                    "specialty": "Family Medicine",
                    "address": "1611 NW 12th Ave, Miami, FL 33130",
                    "phone":   "(305) 555-0203",
                },
                dependents = [],
                medical_history = {
                    "conditions":          ["Eczema", "Asthma (mild)"],
                    "allergies":           ["Dust mites", "Pet dander"],
                    "current_medications": ["Albuterol inhaler (as needed)", "Hydrocortisone cream"],
                    "past_appointments": [
                        {"doctor_name": "Dr. ATIF AHMED",          "npi": "1437396116", "specialty": "Dermatology",      "date": "2025-01-25", "reason": "Eczema flare-up",             "visit_count": 3},
                        {"doctor_name": "Dr. ATIF AHMED",          "npi": "1437396116", "specialty": "Dermatology",      "date": "2024-08-14", "reason": "Eczema management",           "visit_count": 3},
                        {"doctor_name": "Dr. ATIF AHMED",          "npi": "1437396116", "specialty": "Dermatology",      "date": "2024-03-09", "reason": "Skin rash evaluation",        "visit_count": 3},
                        {"doctor_name": "Dr. STEPHANIE ALDAMA",   "npi": "1053414672", "specialty": "Dermatology",      "date": "2024-11-30", "reason": "Asthma + skin allergy review", "visit_count": 1},
                    ],
                },
            ),
            "MEM-10005": User(
                user_id           = "MEM-10005",
                member_id         = "MEM-10005",
                first_name        = "David",
                last_name         = "Chen",
                date_of_birth     = "1982-07-19",
                gender            = "M",
                address           = "233 S Wacker Dr, Apt 8B",
                default_city      = "Chicago",
                default_state     = "IL",
                zip_code          = "60606",
                payer_name        = "Medilife Healthcare",
                insurance_plan_id = "plan-united-platinum",
                insurance_plan    = "Cigna Preferred Medicare (HMO)",
                member_since      = "2023-09-20",
                phone             = "(312) 555-0105",
                preferred_language     = "English",
                smoking_status         = "Never",
                preferred_care_setting = "No preference",
                accessibility_needs    = [],
                assigned_pcp = {
                    "name":    "Dr. Estefania Abasolo Lopez",
                    "npi":     "1043899545",
                    "specialty": "Internal Medicine",
                    "address": "645 N Michigan Ave Ste 530, Chicago, IL 60611",
                    "phone":   "(312) 555-0204",
                },
                dependents = [],
                medical_history = {
                    "conditions":          ["Gastroesophageal Reflux Disease (GERD)", "Knee Osteoarthritis (right)"],
                    "allergies":           [],
                    "current_medications": ["Omeprazole 20mg", "Naproxen 500mg (as needed)"],
                    "past_appointments": [
                        {"doctor_name": "Dr. SINDHU ABRAHAM",     "npi": "1033178223", "specialty": "Gastroenterology",  "date": "2025-02-01", "reason": "GERD follow-up",              "visit_count": 3},
                        {"doctor_name": "Dr. SINDHU ABRAHAM",     "npi": "1033178223", "specialty": "Gastroenterology",  "date": "2024-09-18", "reason": "GERD management",            "visit_count": 3},
                        {"doctor_name": "Dr. SINDHU ABRAHAM",     "npi": "1033178223", "specialty": "Gastroenterology",  "date": "2024-05-07", "reason": "Acid reflux evaluation",     "visit_count": 3},
                        {"doctor_name": "Dr. CODY ANDERSON",      "npi": "1285814244", "specialty": "Orthopaedic Surgery","date": "2024-12-10", "reason": "Right knee pain",            "visit_count": 2},
                        {"doctor_name": "Dr. CODY ANDERSON",      "npi": "1285814244", "specialty": "Orthopaedic Surgery","date": "2024-07-22", "reason": "Knee osteoarthritis review",  "visit_count": 2},
                    ],
                },
            ),
            "MEM-10006": User(
                user_id           = "MEM-10006",
                member_id         = "MEM-10006",
                first_name        = "Priya",
                last_name         = "Patel",
                date_of_birth     = "1992-04-30",
                gender            = "F",
                address           = "500 Convention Way, Unit 7",
                default_city      = "Seattle",
                default_state     = "WA",
                zip_code          = "98101",
                payer_name        = "Medilife Healthcare",
                insurance_plan_id = "plan-bcbs-gold",
                insurance_plan    = "Cigna True Choice Access Medicare (PPO)",
                member_since      = "2022-03-05",
                phone             = "(206) 555-0106",
                preferred_language     = "English",
                smoking_status         = "Never",
                preferred_care_setting = "No preference",
                accessibility_needs    = [],
                assigned_pcp = {
                    "name":    "Dr. Maya Bledsoe",
                    "npi":     "1194730242",
                    "specialty": "Internal Medicine",
                    "address": "1100 9th Ave, Seattle, WA 98115",
                    "phone":   "(206) 555-0205",
                },
                dependents = [],
                medical_history = {
                    "conditions":          ["Rheumatoid Arthritis", "Iron Deficiency Anemia"],
                    "allergies":           ["NSAIDs"],
                    "current_medications": ["Methotrexate 15mg weekly", "Folic Acid 1mg", "Ferrous Sulfate 325mg"],
                    "past_appointments": [
                        {"doctor_name": "Dr. WASSILA AMARI",      "npi": "1164468088", "specialty": "Rheumatology",      "date": "2025-02-20", "reason": "RA medication review",        "visit_count": 4},
                        {"doctor_name": "Dr. WASSILA AMARI",      "npi": "1164468088", "specialty": "Rheumatology",      "date": "2024-11-05", "reason": "RA flare management",         "visit_count": 4},
                        {"doctor_name": "Dr. WASSILA AMARI",      "npi": "1164468088", "specialty": "Rheumatology",      "date": "2024-08-12", "reason": "Joint pain follow-up",        "visit_count": 4},
                        {"doctor_name": "Dr. WASSILA AMARI",      "npi": "1164468088", "specialty": "Rheumatology",      "date": "2024-04-28", "reason": "Initial RA diagnosis",         "visit_count": 4},
                        {"doctor_name": "Dr. TINA BUNCH",         "npi": "1285684803", "specialty": "Rheumatology",      "date": "2024-06-15", "reason": "Second opinion RA",           "visit_count": 1},
                    ],
                },
            ),
        }

    def get_by_id(self, user_id: str) -> User | None:
        key = user_id if user_id.startswith("MEM-") else f"MEM-{user_id}"
        user = self._users.get(key)
        if user:
            from app.services.storage_service import storage
            override = storage.get_plan_override(key)
            if override:
                user.insurance_plan    = override["insurance_plan"]
                user.insurance_plan_id = override["insurance_plan_id"]
        return user

    def update_plan(self, user_id: str, new_plan: str, new_plan_id: str):
        key  = user_id if user_id.startswith("MEM-") else f"MEM-{user_id}"
        user = self._users.get(key)
        if user:
            user.insurance_plan    = new_plan
            user.insurance_plan_id = new_plan_id

    def authenticate(self, member_id: str, password: str) -> User | None:
        key = member_id if member_id.startswith("MEM-") else f"MEM-{member_id}"
        if _PASSWORDS.get(key) == password:
            return self.get_by_id(key)
        return None

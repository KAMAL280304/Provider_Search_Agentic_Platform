"""
Mock Appointment Service.
Generates realistic operational hours + available slots for any provider.
Stores bookings in-memory. No DB needed.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import Optional


# ── Operational hour templates ────────────────────────────────────────────────
_SCHEDULES = [
    {"days": [0, 1, 2, 3, 4],       "start": "08:00", "end": "17:00"},
    {"days": [0, 1, 2, 3, 4],       "start": "09:00", "end": "17:30"},
    {"days": [0, 1, 2, 3, 4, 5],    "start": "08:00", "end": "13:00"},
    {"days": [1, 2, 3, 4],          "start": "10:00", "end": "17:00"},
    {"days": [0, 2, 4],             "start": "08:00", "end": "16:00"},
]

_SLOT_DURATION_MIN = 30


class AppointmentMockService:
    """
    Generates and manages mock appointment slots for any provider.
    Slots are generated on-demand and cached in memory.
    """

    def __init__(self):
        # provider_id → {slot_id → slot_dict}
        self._slots:    dict[str, dict[str, dict]] = {}
        # provider_id → schedule template
        self._schedules: dict[str, dict] = {}
        # appointment_id → appointment_dict
        self._appointments: dict[str, dict] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def get_slots(self, provider_id: str, provider_name: str) -> dict:
        """
        Returns available slots for the next 7 days grouped by date.
        Generates slots on first call, returns cached on subsequent calls.
        """
        if provider_id not in self._slots:
            self._generate_slots(provider_id)

        today      = datetime.now().date()
        next_7days = [today + timedelta(days=i) for i in range(1, 8)]

        grouped: dict[str, list] = {}
        for day in next_7days:
            date_str = day.strftime("%Y-%m-%d")
            day_slots = [
                s for s in self._slots[provider_id].values()
                if s["date"] == date_str and s["status"] == "free"
            ]
            if day_slots:
                grouped[date_str] = sorted(day_slots, key=lambda x: x["start_time"])

        return {
            "provider_id":   provider_id,
            "provider_name": provider_name,
            "slots_by_date": grouped,
            "total_available": sum(len(v) for v in grouped.values()),
        }

    def book_slot(
        self,
        provider_id:   str,
        provider_name: str,
        slot_id:       str,
        user_id:       str,
        care_type:     str = "in_person",
    ) -> dict:
        """Books a slot. Returns appointment confirmation or error."""
        if provider_id not in self._slots:
            self._generate_slots(provider_id)

        slot = self._slots[provider_id].get(slot_id)
        if not slot:
            return {"success": False, "error": "Slot not found."}
        if slot["status"] != "free":
            return {"success": False, "error": "This slot is no longer available. Please choose another."}

        # Mark slot as booked
        slot["status"] = "busy"

        appointment_id = f"APT-{uuid.uuid4().hex[:8].upper()}"
        appointment = {
            "appointment_id": appointment_id,
            "provider_id":    provider_id,
            "provider_name":  provider_name,
            "user_id":        user_id,
            "date":           slot["date"],
            "start_time":     slot["start_time"],
            "end_time":       slot["end_time"],
            "care_type":      care_type,
            "status":         "confirmed",
            "booked_at":      datetime.utcnow().isoformat(),
        }
        self._appointments[appointment_id] = appointment
        return {"success": True, "appointment": appointment}

    def get_appointment(self, appointment_id: str) -> Optional[dict]:
        return self._appointments.get(appointment_id)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _generate_slots(self, provider_id: str):
        """Generate slots for next 7 days based on a random schedule template."""
        schedule = random.choice(_SCHEDULES)
        self._schedules[provider_id] = schedule
        self._slots[provider_id]     = {}

        today      = datetime.now().date()
        next_7days = [today + timedelta(days=i) for i in range(1, 8)]

        for day in next_7days:
            # Skip days not in this provider's schedule
            if day.weekday() not in schedule["days"]:
                continue

            start_dt = datetime.strptime(f"{day} {schedule['start']}", "%Y-%m-%d %H:%M")
            end_dt   = datetime.strptime(f"{day} {schedule['end']}",   "%Y-%m-%d %H:%M")
            current  = start_dt

            while current + timedelta(minutes=_SLOT_DURATION_MIN) <= end_dt:
                slot_end = current + timedelta(minutes=_SLOT_DURATION_MIN)
                slot_id  = f"slot-{provider_id}-{current.strftime('%Y%m%d%H%M')}"

                # Randomly pre-book ~30% of slots to simulate realistic availability
                status = "busy" if random.random() < 0.3 else "free"

                self._slots[provider_id][slot_id] = {
                    "slot_id":    slot_id,
                    "date":       day.strftime("%Y-%m-%d"),
                    "start_time": current.strftime("%H:%M"),
                    "end_time":   slot_end.strftime("%H:%M"),
                    "status":     status,
                }
                current = slot_end


# Singleton
appointment_mock_service = AppointmentMockService()

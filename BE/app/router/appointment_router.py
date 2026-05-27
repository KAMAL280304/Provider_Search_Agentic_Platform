from fastapi import APIRouter, Request
from app.services.storage_service import storage

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("/{member_id}")
def get_member_appointments(member_id: str):
    """Return all appointments for a member (upcoming + past)."""
    appointments = storage.read(f"appointments/{member_id}.json") or []
    return {"appointments": appointments}


@router.post("/{member_id}")
async def save_member_appointment(member_id: str, request: Request):
    """Save a confirmed appointment for a member (called by frontend after booking)."""
    body = await request.json()
    key = f"appointments/{member_id}.json"
    appts = storage.read(key) or []

    # Avoid duplicates — same provider + date
    sig = f"{body.get('provider', '')}|{body.get('date', '')}"
    existing_keys = {f"{a.get('provider', '')}|{a.get('date', '')}" for a in appts}
    if sig not in existing_keys:
        appts.append({
            "provider":          body.get("provider", ""),
            "date":              body.get("date", ""),
            "time":              body.get("time", ""),
            "consultation_type": body.get("consultation_type", ""),
            "address":           body.get("address", ""),
            "reason":            body.get("reason", ""),
        })
        storage.write(key, appts)

    return {"success": True, "appointments": appts}

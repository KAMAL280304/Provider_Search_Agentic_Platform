from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.repositories.user_repo import UserRepository, DEMO_TRAVEL_OVERRIDES
from app.app_logging.audit_logger import audit_logger
from app.services.storage_service import storage

router = APIRouter(tags=["Auth"])
_repo  = UserRepository()


class LoginRequest(BaseModel):
    member_id: str
    password:  str


@router.post("/login")
def login(payload: LoginRequest):
    user = _repo.authenticate(payload.member_id, payload.password)
    if not user:
        audit_logger.log_event("LOGIN_FAILED", payload.member_id, {"reason": "Invalid credentials"})
        raise HTTPException(status_code=401, detail="Invalid member ID or password")

    plan_override = storage.get_plan_override(user.member_id)
    actual_plan = plan_override["insurance_plan"] if plan_override else user.insurance_plan

    audit_logger.log_event("USER_LOGIN", user.member_id, {
        "name":           f"{user.first_name} {user.last_name}",
        "insurance_plan": actual_plan,
        "city":           user.default_city,
        "state":          user.default_state,
    })

    travel = DEMO_TRAVEL_OVERRIDES.get(user.member_id, {})
    plan_change_detected = storage.read(f"plan_change/{user.member_id}.json") is not None

    return {
        "success": True,
        "plan_change_detected": plan_change_detected,
        "member": {
            "member_id":      user.member_id,
            "first_name":     user.first_name,
            "last_name":      user.last_name,
            "date_of_birth":  user.date_of_birth,
            "gender":         user.gender,
            "address":        user.address,
            "city":           user.default_city,
            "state":          user.default_state,
            "zip":            user.zip_code,
            "payer_name":     user.payer_name,
            "insurance_plan": actual_plan,
            "member_since":   user.member_since,
            "dependents":     user.dependents,
            "travel_city":    travel.get("city", ""),
            "travel_state":   travel.get("state", ""),
        },
    }


class PlanChangeRequest(BaseModel):
    user_id:     str
    new_plan:    str
    new_plan_id: str
    reason:      str = ""


@router.post("/update-plan")
def update_plan(payload: PlanChangeRequest):
    user = _repo.get_by_id(payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    previous_plan    = user.insurance_plan
    previous_plan_id = user.insurance_plan_id
    storage.save_plan_change(payload.user_id, previous_plan, previous_plan_id, new_plan=payload.new_plan, new_plan_id=payload.new_plan_id)
    _repo.update_plan(payload.user_id, payload.new_plan, payload.new_plan_id)
    storage.update_plan(payload.user_id, payload.new_plan, payload.new_plan_id)
    return {"success": True, "previous_plan": previous_plan, "new_plan": payload.new_plan}


@router.post("/logout")
def logout(payload: dict = None):
    payload = payload or {}
    user_id = payload.get("user_id", "")
    if user_id:
        from app.adk.agent import _adk_sessions, _runners
        _adk_sessions.pop(user_id, None)
        for k in [k for k in list(_runners.keys()) if k.startswith(f"{user_id}|")]:
            _runners.pop(k, None)
    return {"success": True}

"""
Dashboard Router — Provider & Payer portal endpoints.
All endpoints read/write the same storage files the agent uses.
Zero changes to agent, storage_service, or any existing router.
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.storage_service import storage
from app.db.repositories.user_repo import UserRepository

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
_repo  = UserRepository()

MEMBER_IDS = ["MEM-10001", "MEM-10002", "MEM-10003", "MEM-10004", "MEM-10005", "MEM-10006"]


def _member_summary(member_id: str) -> dict:
    user = _repo.get_by_id(member_id)
    if not user:
        return {}
    mri_rx     = storage.get_mri_prescription(member_id)
    prior_auth = storage.get_prior_auth(member_id)
    referral   = storage.get_referral(member_id)
    pcp_changes = storage.read(f"pcp_changes/{member_id}.json") or []
    plan_change = storage.read(f"plan_change/{member_id}.json")
    notifications = [
        n for n in (storage.read("notifications/all.json") or [])
        if n.get("member_id") == member_id
    ]
    bookings = storage.get_bookings(member_id)
    return {
        "member_id":      member_id,
        "name":           f"{user.first_name} {user.last_name}",
        "plan":           user.insurance_plan,
        "city":           f"{user.default_city}, {user.default_state}",
        "assigned_pcp":   user.assigned_pcp,
        "conditions":     user.medical_history.get("conditions", []),
        "medications":    user.medical_history.get("current_medications", []),
        "mri_rx":         mri_rx,
        "prior_auth":     prior_auth,
        "referral":       referral,
        "pcp_changes":    pcp_changes,
        "plan_change":    plan_change,
        "notifications":  notifications[-10:],
        "bookings":       bookings,
    }


# ── GET all members overview ──────────────────────────────────────────────────

@router.get("/members")
async def get_all_members():
    import asyncio
    from fastapi.concurrency import run_in_threadpool
    summaries = await asyncio.gather(
        *[run_in_threadpool(_member_summary, mid) for mid in MEMBER_IDS]
    )
    return {"members": [s for s in summaries if s]}


@router.get("/member/{member_id}")
def get_member(member_id: str):
    data = _member_summary(member_id)
    if not data:
        raise HTTPException(status_code=404, detail="Member not found")
    return data


# ── PROVIDER actions ──────────────────────────────────────────────────────────

class MRIPrescriptionRequest(BaseModel):
    member_id:    str
    body_part:    str
    reason:       str
    prescribed_by_name:    str
    prescribed_by_specialty: str = "Neurology"

@router.post("/provider/send-mri-prescription")
def send_mri_prescription(req: MRIPrescriptionRequest):
    """Provider writes MRI prescription for a member."""
    storage.update_mri_prescription(req.member_id, {
        "prescription_mri": True,
        "body_part":        req.body_part,
        "reason":           req.reason,
        "prescribed_by": {
            "name":      req.prescribed_by_name,
            "specialty": req.prescribed_by_specialty,
        },
        "prescribed_date": datetime.utcnow().strftime("%Y-%m-%d"),
    })
    # Initialise prior auth as none so agent can pick it up
    existing_pa = storage.get_prior_auth(req.member_id)
    if not existing_pa:
        storage.save_prior_auth(req.member_id, {
            "status":     "none",
            "created_at": datetime.utcnow().isoformat(),
            "payer":      "Cigna",
        })
    # Invalidate agent runner so next turn sees new prescription
    try:
        from app.adk.agent import _runners
        for k in [k for k in list(_runners.keys()) if k.startswith(f"{req.member_id}|")]:
            _runners.pop(k, None)
    except Exception:
        pass
    return {"success": True, "message": f"MRI prescription sent for {req.member_id}"}


class MriRequiredRequest(BaseModel):
    member_id:     str
    provider_name: str
    date:          str
    time_start:    str
    mri_required:  bool

@router.post("/provider/toggle-mri-required")
def toggle_mri_required(req: MriRequiredRequest):
    """Provider marks whether an MRI scan is required after a specialist visit."""
    bookings = storage.get_bookings(req.member_id)
    matched = False
    for b in bookings:
        if (
            b.get("provider_name", "").lower() == req.provider_name.lower()
            and b.get("date") == req.date
            and b.get("time_start") == req.time_start
        ):
            b["mri_required"] = req.mri_required
            matched = True
    if matched:
        storage.write(f"bookings/{req.member_id}.json", bookings)
        try:
            from app.adk.agent import _runners
            for k in [k for k in list(_runners.keys()) if k.startswith(f"{req.member_id}|")]:
                _runners.pop(k, None)
        except Exception:
            pass
    return {"success": matched, "mri_required": req.mri_required}


class PCPAcceptRequest(BaseModel):
    member_id: str

@router.post("/provider/accept-pcp-assignment")
def accept_pcp_assignment(req: PCPAcceptRequest):
    """New PCP's office accepts the incoming patient assignment."""
    pcp_changes = storage.read(f"pcp_changes/{req.member_id}.json") or []
    updated = False
    for change in pcp_changes:
        if change.get("status") == "completed":
            change["provider_accepted"]    = True
            change["provider_accepted_at"] = datetime.utcnow().isoformat()
            updated = True
    if updated:
        storage.write(f"pcp_changes/{req.member_id}.json", pcp_changes)
    return {"success": True, "message": "PCP assignment accepted by provider"}


# ── Mark appointment completed ────────────────────────────────────────────────

class AppointmentCompleteRequest(BaseModel):
    member_id:     str
    provider_name: str
    date:          str
    time_start:    str
    visit_notes:   str = ""   # optional clinical notes the provider adds

@router.post("/provider/complete-appointment")
def complete_appointment(req: AppointmentCompleteRequest):
    """
    Provider marks an appointment as completed after the patient visit.
    This is the trigger that unlocks:
      - PCP → Create Referral button
      - Specialist → Write Prescription button
    """
    bookings = storage.get_bookings(req.member_id)
    matched  = False
    for b in bookings:
        if (
            b.get("provider_name", "").lower() == req.provider_name.lower()
            and b.get("date") == req.date
            and b.get("time_start") == req.time_start
        ):
            b["status"]       = "completed"
            b["completed_at"] = datetime.utcnow().isoformat()
            if req.visit_notes:
                b["visit_notes"] = req.visit_notes
            matched = True
    if matched:
        storage.write(f"bookings/{req.member_id}.json", bookings)
        # Invalidate runner so agent sees updated booking status on next message
        try:
            from app.adk.agent import _runners
            for k in [k for k in list(_runners.keys()) if k.startswith(f"{req.member_id}|")]:
                _runners.pop(k, None)
        except Exception:
            pass
    return {"success": matched, "message": "Appointment marked as completed" if matched else "Appointment not found"}


# ── Create Referral (PCP-initiated, independent of agent) ─────────────────────

class CreateReferralRequest(BaseModel):
    member_id:    str
    specialist:   str           # e.g. "Orthopaedic Surgery"
    approved_by:  str           # PCP name
    reason:       str = ""      # clinical reason for referral
    valid_days:   int = 30      # how many days the referral is valid

@router.post("/provider/create-referral")
def create_referral(req: CreateReferralRequest):
    """
    PCP creates a referral after completing the appointment.
    This is the real-world flow: PCP sees patient → decides referral needed → creates it.
    The agent reads this on the member's next login and proactively books the specialist.
    """
    now = datetime.utcnow()
    data = {
        "status":        "approved",
        "specialist":    req.specialist,
        "approved_by":   req.approved_by,
        "reason":        req.reason,
        "approved_date": now.strftime("%Y-%m-%d"),
        "valid_through": (now + timedelta(days=req.valid_days)).strftime("%Y-%m-%d"),
        "created_at":    now.isoformat(),
    }
    storage.save_referral(req.member_id, data)
    # Invalidate runner so agent picks up referral on next session
    try:
        from app.adk.agent import _runners
        for k in [k for k in list(_runners.keys()) if k.startswith(f"{req.member_id}|")]:
            _runners.pop(k, None)
    except Exception:
        pass
    return {"success": True, "message": f"Referral created for {req.specialist}", "referral": data}


class PriorAuthSubmitRequest(BaseModel):
    member_id:      str
    ordering_doctor: str
    procedure:      str = "MRI Scan"

@router.post("/provider/submit-prior-auth")
def submit_prior_auth(req: PriorAuthSubmitRequest):
    """Provider's office submits prior auth request to payer."""
    now = datetime.utcnow()
    existing = storage.get_prior_auth(req.member_id) or {}
    existing.update({
        "status":         "pending",
        "submitted_by":   req.ordering_doctor,
        "submitted_date": now.strftime("%Y-%m-%d"),
        "procedure":      req.procedure,
        "payer":          "Cigna",
        "auth_reference_number": f"PA-{now.strftime('%Y%m%d')}-{req.member_id[-5:]}",
    })
    storage.save_prior_auth(req.member_id, existing)
    try:
        from app.adk.agent import _runners
        for k in [k for k in list(_runners.keys()) if k.startswith(f"{req.member_id}|")]:
            _runners.pop(k, None)
    except Exception:
        pass
    return {"success": True, "status": "pending", "ref": existing["auth_reference_number"]}


class ReferralApprovalRequest(BaseModel):
    member_id:   str
    specialist:  str
    approved_by: str   # PCP name

@router.post("/provider/approve-referral")
def approve_referral(req: ReferralApprovalRequest):
    """PCP's office approves a specialist referral — agent reads this to unblock booking."""
    now = datetime.utcnow()
    data = {
        "status":        "approved",
        "specialist":    req.specialist,
        "approved_by":   req.approved_by,
        "approved_date": now.strftime("%Y-%m-%d"),
        "valid_through": (now + timedelta(days=30)).strftime("%Y-%m-%d"),
    }
    storage.save_referral(req.member_id, data)
    try:
        from app.adk.agent import _runners
        for k in [k for k in list(_runners.keys()) if k.startswith(f"{req.member_id}|")]:
            _runners.pop(k, None)
    except Exception:
        pass
    return {"success": True, "message": f"Referral approved for {req.specialist}"}


# ── PAYER actions ─────────────────────────────────────────────────────────────

class PriorAuthDecisionRequest(BaseModel):
    member_id: str
    decision:  str   # "approved" or "declined"

@router.post("/payer/prior-auth-decision")
def prior_auth_decision(req: PriorAuthDecisionRequest):
    """Payer approves or declines a prior auth request."""
    if req.decision not in ("approved", "declined"):
        raise HTTPException(status_code=400, detail="decision must be 'approved' or 'declined'")
    pa = storage.get_prior_auth(req.member_id)
    if not pa:
        raise HTTPException(status_code=404, detail="No prior auth on file for this member")
    now = datetime.utcnow()
    pa["status"] = req.decision
    if req.decision == "approved":
        pa["approved_date"]  = now.strftime("%Y-%m-%d")
        pa["valid_through"]  = (now + timedelta(days=90)).strftime("%Y-%m-%d")
    else:
        pa["declined_date"]  = now.strftime("%Y-%m-%d")
        pa["decline_reason"] = "Not medically necessary per Cigna review"
    storage.save_prior_auth(req.member_id, pa)
    try:
        from app.adk.agent import _runners
        for k in [k for k in list(_runners.keys()) if k.startswith(f"{req.member_id}|")]:
            _runners.pop(k, None)
    except Exception:
        pass
    return {"success": True, "status": req.decision}


class PCPChangeDecisionRequest(BaseModel):
    member_id: str
    decision:  str   # "approved" or "declined"

@router.post("/payer/pcp-change-decision")
def pcp_change_decision(req: PCPChangeDecisionRequest):
    """Payer approves or declines a PCP change request."""
    if req.decision not in ("approved", "declined"):
        raise HTTPException(status_code=400, detail="decision must be 'approved' or 'declined'")
    pcp_changes = storage.read(f"pcp_changes/{req.member_id}.json") or []
    now = datetime.utcnow()
    updated = False
    for change in pcp_changes:
        if change.get("status") == "pending":
            change["status"]       = "completed" if req.decision == "approved" else "declined"
            change["completed_at"] = now.isoformat()
            updated = True
            # If approved, persist the new PCP override
            if req.decision == "approved":
                new_pcp = {
                    "name":      change.get("new_pcp_name", ""),
                    "npi":       change.get("new_pcp_npi", ""),
                    "specialty": "Family Medicine",
                    "address":   change.get("new_pcp_address", ""),
                    "phone":     "",
                }
                storage.update_pcp(req.member_id, new_pcp)
                _repo.update_plan(req.member_id, _repo.get_by_id(req.member_id).insurance_plan,
                                  _repo.get_by_id(req.member_id).insurance_plan_id)
    if updated:
        storage.write(f"pcp_changes/{req.member_id}.json", pcp_changes)
    try:
        from app.adk.agent import _runners, _adk_sessions
        for k in [k for k in list(_runners.keys()) if k.startswith(f"{req.member_id}|")]:
            _runners.pop(k, None)
    except Exception:
        pass
    return {"success": True, "decision": req.decision}


class PlanChangeDecisionRequest(BaseModel):
    member_id: str
    decision:  str   # "approved" or "declined"

@router.post("/payer/plan-change-decision")
def plan_change_decision(req: PlanChangeDecisionRequest):
    """Payer approves or declines a plan change request."""
    if req.decision not in ("approved", "declined"):
        raise HTTPException(status_code=400, detail="decision must be 'approved' or 'declined'")
    plan_change = storage.read(f"plan_change/{req.member_id}.json")
    if not plan_change:
        raise HTTPException(status_code=404, detail="No pending plan change for this member")
    now = datetime.utcnow()
    plan_change["payer_decision"]    = req.decision
    plan_change["payer_decided_at"]  = now.isoformat()
    if req.decision == "declined":
        # Revert the plan_override so the member stays on their original plan
        storage.delete(f"plan_override/{req.member_id}.json")
        # Also revert in-memory user object to previous plan
        prev_plan    = plan_change.get("previous_plan", "")
        prev_plan_id = plan_change.get("previous_plan_id", "")
        if prev_plan:
            _repo.update_plan(req.member_id, prev_plan, prev_plan_id)
        # Keep plan_change file so the proactive block can inform the member
        storage.write(f"plan_change/{req.member_id}.json", plan_change)
    else:
        storage.write(f"plan_change/{req.member_id}.json", plan_change)
    try:
        from app.adk.agent import _runners
        for k in [k for k in list(_runners.keys()) if k.startswith(f"{req.member_id}|")]:
            _runners.pop(k, None)
    except Exception:
        pass
    return {"success": True, "decision": req.decision}

"""
Standard response format for all tool functions.

Rules:
- All tools MUST use create_response()
- No tool should return free-text instructions
- All decisions must be represented using:
    - reason_code
    - next_action
- This ensures deterministic system behavior
"""

from __future__ import annotations


# ── Reason Codes ──────────────────────────────────────────────────────────────

class ReasonCodes:
    """
    Machine-readable codes that identify WHY a tool returned a particular result.

    The LLM agent reads reason_code to decide what to say and what to do next.
    These replace all free-text instruction strings previously embedded in
    tool responses.

    Usage:
        from app.utils.response import ReasonCodes
        reason_code=ReasonCodes.HMO_REFERRAL_REQUIRED
    """

    # ── Blocking reasons ──────────────────────────────────────────────────────

    HMO_REFERRAL_REQUIRED = "HMO_REFERRAL_REQUIRED"
    """
    Member is on an HMO plan and no approved referral is on file.
    Specialist search or booking is blocked.
    next_action will be BOOK_PCP.
    """

    PRIOR_AUTH_REQUIRED = "PRIOR_AUTH_REQUIRED"
    """
    An imaging/MRI booking was attempted but prior authorization has not
    been approved by the payer yet (status is 'none' or 'pending').
    Booking is blocked until payer approves.
    next_action will be NOTIFY_PROVIDER (if status=none) or NONE (if status=pending).
    """

    MRI_PRESCRIPTION_EXISTS = "MRI_PRESCRIPTION_EXISTS"
    """
    A provider search was attempted for a specialty/body part that already
    has an MRI prescription on file. The clinical journey is past the
    'see a doctor' stage — no new provider search is needed.
    next_action depends on prior_auth_status in data.
    """

    EMERGENCY_CASE = "EMERGENCY_CASE"
    """
    The urgency level passed to find_providers was 'emergency'.
    Member must call 911 immediately. No provider search performed.
    next_action will be NONE.
    """

    OUT_OF_NETWORK = "OUT_OF_NETWORK"
    """
    The specific doctor requested by name is out-of-network under the
    member's current plan. Member must confirm before proceeding.
    next_action will be NONE (wait for member decision).
    """

    REFERRAL_NOT_ALLOWED = "REFERRAL_NOT_ALLOWED"
    """
    notify_provider was called with notification_type='referral_request'.
    This is not allowed — referrals are raised by PCPs after a physical
    visit, not by this application.
    next_action will be NONE.
    """

    PRIOR_AUTH_SUBMISSION_NOT_ALLOWED = "PRIOR_AUTH_SUBMISSION_NOT_ALLOWED"
    """
    An attempt was made to submit prior authorization on behalf of the member.
    This is not allowed — prior auth is submitted by the specialist's office,
    not by this application. Only follow-up reminders are permitted.
    next_action will be NONE.
    """

    PPO_REFERRAL_NOT_REQUIRED = "PPO_REFERRAL_NOT_REQUIRED"
    """
    notify_provider was called with notification_type='referral_request'
    for a PPO member. PPO plans do not require referrals — this call
    is blocked as unnecessary.
    next_action will be NONE.
    """

    # ── Success reasons ───────────────────────────────────────────────────────

    SUCCESS = "SUCCESS"
    """
    Tool executed successfully. Result data is in the data field.
    next_action indicates what the agent should do next.
    """

    OON_FALLBACK = "OON_FALLBACK"
    """
    No in-network providers were found. Results contain out-of-network
    providers as a fallback. Member must be informed before proceeding.
    next_action will be NONE (wait for member confirmation).
    """

    IMAGING_GATE_APPROVED = "IMAGING_GATE_APPROVED"
    """
    Imaging search was performed and prior auth is already approved.
    Booking can proceed normally.
    next_action will be CHECK_AVAILABILITY.
    """

    IMAGING_GATE_PENDING = "IMAGING_GATE_PENDING"
    """
    Imaging search was performed but prior auth is pending payer review.
    Show imaging centers but do NOT call check_availability or book_appointment.
    next_action will be NONE.
    """

    IMAGING_GATE_NONE = "IMAGING_GATE_NONE"
    """
    Imaging search was performed but prior auth has not been submitted yet.
    Show imaging centers, call notify_provider to remind specialist's office.
    next_action will be NOTIFY_PROVIDER.
    """


# ── Next Actions ──────────────────────────────────────────────────────────────

class Actions:
    """
    Machine-readable codes that tell the LLM agent what tool to call next,
    or what action to take after reading this tool's response.

    These replace all "IMMEDIATELY call find_providers..." instruction strings
    previously embedded in tool responses.

    Usage:
        from app.utils.response import Actions
        next_action=Actions.BOOK_PCP
    """

    BOOK_PCP = "BOOK_PCP"
    """
    Call find_providers with specialty='Primary Care' and the member's
    assigned PCP name, then call check_availability.
    Used when HMO gate fires — redirect to PCP before specialist.
    """

    CHECK_AVAILABILITY = "CHECK_AVAILABILITY"
    """
    Call check_availability on the top_pick provider from the data field.
    Used after a successful find_providers call.
    """

    PROCEED_BOOKING = "PROCEED_BOOKING"
    """
    Proceed with book_appointment using the slot the member selected.
    Used when prior auth is approved and member has chosen a time slot.
    """

    NOTIFY_PROVIDER = "NOTIFY_PROVIDER"
    """
    Call notify_provider with notification_type='prior_auth_request' targeting
    the prescribing_doctor in the data field.
    Used when MRI prescription is on file but prior auth has not been submitted.
    """

    NONE = None
    """
    No automatic next action. Wait for member input or inform member of status.
    Used for blocked responses, OON fallbacks, and status-only responses.
    """


# ── Core Response Builder ─────────────────────────────────────────────────────

def create_response(
    allowed: bool = True,
    blocked: bool = False,
    reason_code: str = None,
    next_action: str = None,
    data: dict = None,
    error: str = None,
) -> dict:
    """
    Build a standardized tool response dict.

    Parameters
    ----------
    allowed : bool
        True if the requested operation is permitted to proceed.
    blocked : bool
        True if a hard business rule gate has prevented the operation.
        When blocked=True, allowed should be False.
    reason_code : str | None
        A ReasonCodes constant explaining WHY this response was produced.
    next_action : str | None
        An Actions constant telling the LLM what tool to call next.
        None means wait for member input or no further action needed.
    data : dict | None
        Structured payload. No free-text instruction strings.
    error : str | None
        Human-readable error message when an unexpected failure occurred.
        None on all non-error paths.

    Returns
    -------
    dict
        {
            "allowed":     bool,
            "blocked":     bool,
            "reason_code": str | None,
            "next_action": str | None,
            "data":        dict,
            "error":       str | None,
        }
    """
    return {
        "allowed":     allowed,
        "blocked":     blocked,
        "reason_code": reason_code,
        "next_action": next_action,
        "data":        data or {},
        "error":       error,
    }

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

from app.utils.response import Actions

_KNOWN_ACTIONS = {Actions.BOOK_PCP, Actions.CHECK_AVAILABILITY, Actions.NOTIFY_PROVIDER}


def handle_tool_response(response: dict) -> dict:
    """
    Inspect a tool response and return the next system action.

    Returns one of three types:
      "explain"   — blocked by a business rule; surface reason_code to the agent
      "call_tool" — chain to the next tool automatically
      "final"     — terminal; no further tool call needed
    """
    blocked     = response.get("blocked", False)
    next_action = response.get("next_action")
    data        = response.get("data", {})

    print(
        f"[CONTROLLER] blocked={blocked} "
        f"next_action={next_action} "
        f"reason={response.get('reason_code')}"
    )

    # ── 1. Blocked ────────────────────────────────────────────────────────────
    if blocked:
        return {
            "type":        "explain",
            "reason_code": response.get("reason_code"),
            "data":        data,
        }

    # ── 2. Action routing ─────────────────────────────────────────────────────
    if next_action not in _KNOWN_ACTIONS:
        return {"type": "final", "data": data}

    if next_action == Actions.BOOK_PCP:
        return {
            "type":   "call_tool",
            "tool":   "find_providers",
            "params": {"specialty": "primary care"},
        }

    if next_action == Actions.CHECK_AVAILABILITY:
        provider = data.get("top_provider")
        if not provider:
            return {"type": "final", "data": data}
        return {
            "type":   "call_tool",
            "tool":   "check_availability",
            "params": {"provider": provider},
        }

    if next_action == Actions.NOTIFY_PROVIDER:
        return {
            "type":   "call_tool",
            "tool":   "notify_provider",
            "params": data,
        }

    # ── 3. Success / terminal ─────────────────────────────────────────────────
    if response.get("allowed") and next_action is None:
        return {"type": "final", "data": data}

    # ── 4. Fallback ───────────────────────────────────────────────────────────
    return {"type": "final", "data": data}

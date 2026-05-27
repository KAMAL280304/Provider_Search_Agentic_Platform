import json
import asyncio
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from app.adk.agent import run_adk_agent_stream
from app.app_logging.audit_logger import audit_logger
from app.services.storage_service import storage

router = APIRouter()


def _get_user_id(body: dict) -> str:
    user_id = body.get("user_id") or body.get("member_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    return user_id


@router.post("/chat")
async def chat(request: Request):
    body    = await request.json()
    user_id = _get_user_id(body)
    message = body.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="message field required")

    audit_logger.log_event("CHAT_REQUEST", user_id, {"message": message[:200]})

    final = {"type": "error", "message": "No response"}
    travel_city  = body.get("travel_city",  "")
    travel_state = body.get("travel_state", "")
    async for event in run_adk_agent_stream(message, user_id, travel_city=travel_city, travel_state=travel_state):

        if event["type"] == "final":
            final = event["response"]

    audit_logger.log_event("CHAT_RESPONSE", user_id, {
        "response_type":   final.get("type"),
        "providers_count": len(final.get("providers", [])),
    })
    return final


@router.post("/chat/stream")
async def chat_stream(request: Request):
    body    = await request.json()
    user_id = _get_user_id(body)
    message = body.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="message field required")

    audit_logger.log_event("CHAT_REQUEST", user_id, {"message": message[:200]})

    travel_city  = body.get("travel_city",  "")
    travel_state = body.get("travel_state", "")
    previous_plan = body.get("previous_plan", "")
    new_plan      = body.get("new_plan", "")

    async def event_generator():
        final_event    = None
        tool_calls_log = []   # accumulate tool calls for per-session summarization

        async for event in run_adk_agent_stream(message, user_id, travel_city=travel_city, travel_state=travel_state, previous_plan=previous_plan, new_plan=new_plan):

            yield f"data: {json.dumps(event)}\n\n"
            if event["type"] == "tool_call":
                tool_calls_log.append({
                    "tool":    event.get("tool"),
                    "thought": event.get("thought", ""),
                    "input":   event.get("input", {}),
                })
            if event["type"] == "tool_result":
                # Attach the decision to the matching tool_call entry
                if tool_calls_log and tool_calls_log[-1]["tool"] == event.get("tool"):
                    tool_calls_log[-1]["decision"] = event.get("decision", "")
            if event["type"] == "final":
                final_event = event["response"]
        yield "data: [DONE]\n\n"

        if final_event:
            audit_logger.log_event("CHAT_RESPONSE", user_id, {
                "response_type":   final_event.get("type"),
                "providers_count": len(final_event.get("providers", [])),
            })
            audit_logger.log_conversation_turn(user_id, user_id, "user", message)
            reply = (
                final_event.get("explanation") or
                final_event.get("question")    or
                final_event.get("message", "")
            )
            if reply:
                audit_logger.log_conversation_turn(user_id, user_id, "assistant", reply)

            # ── Per-session summarization ─────────────────────────────────────
            # If tools were called this turn, generate a session summary and save it.
            # This ensures the agent always has a written record of what happened —
            # not just raw turns that only get compressed after 50+ messages.
            if tool_calls_log and reply and message not in ("__session_start__",):
                try:
                    loop = asyncio.get_event_loop()
                    loop.create_task(
                        _save_session_summary(user_id, message, reply, tool_calls_log)
                    )
                except Exception:
                    pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


async def _save_session_summary(
    user_id: str,
    user_message: str,
    agent_reply: str,
    tool_calls_log: list,
) -> None:
    """
    Build a concise session summary from the tool chain that just ran and
    save it via StorageService._save_summary_entry so it feeds into the
    agent's long-term memory immediately — not just after 50 turns.
    """
    try:
        from app.services.llm_service import LLMService
        llm = LLMService()

        # Build a readable tool trace for the LLM to summarize
        tool_trace_lines = []
        for tc in tool_calls_log:
            tool_trace_lines.append(f"  [{tc['tool']}]")
            if tc.get("thought"):
                tool_trace_lines.append(f"    Why: {tc['thought']}")
            if tc.get("decision"):
                tool_trace_lines.append(f"    Result: {tc['decision']}")
        tool_trace = "\n".join(tool_trace_lines) if tool_trace_lines else "  (no tools called)"

        prompt = f"""Summarize this single healthcare assistant interaction into 1-2 sentences.
Focus on: what the member asked, what was found/booked/notified, and any key decision made.
Be factual and specific (include doctor names, dates, prior auth status if relevant).
No filler words. Past tense.

Member said: {user_message[:300]}

Agent used these tools:
{tool_trace}

Agent replied: {agent_reply[:400]}

Summary (1-2 sentences):"""

        summary = llm.generate_text(prompt).strip()
        if summary:
            storage._save_summary_entry(user_id, summary)
    except Exception as e:
        print(f"[chat_router] Session summary error for {user_id}: {e}")

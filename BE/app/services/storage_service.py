"""
StorageService — unified storage interface.

STORAGE_BACKEND=local  → reads/writes local JSON files under logs/storage/
STORAGE_BACKEND=gcs    → reads/writes GCS bucket blobs

Storage layout:
  bookings/{member_id}.json           — confirmed appointments (permanent)
  conversations/{member_id}.json      — last 20 turns (current session context)
  history_summary/{member_id}.json    — rolling summaries (last 12 months)
  long_term_profile/{member_id}.json  — permanent compressed profile (never deleted)
  notifications/all.json              — provider notifications

History management:
  - Turns > 50 → compress oldest 30 into a summary entry → keep latest 20 → delete the 30
  - Summary entries older than 12 months → merge into long_term_profile → delete old entries
  - Compression is async (background) — never blocks the user response
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.config import settings

# Thresholds
_TURNS_COMPRESS_THRESHOLD = 50   # compress when turns exceed this
_TURNS_TO_COMPRESS        = 30   # how many old turns to compress at once
_TURNS_TO_KEEP            = 20   # always keep this many recent turns
_SUMMARY_MAX_MONTHS       = 12   # compress summaries older than this


class StorageService:

    def __init__(self):
        self.backend = settings.STORAGE_BACKEND
        if self.backend == "gcs":
            from google.cloud import storage as gcs
            self._client = gcs.Client(project=settings.GCP_PROJECT_ID)
            self._bucket = self._client.bucket(settings.GCS_BUCKET_NAME)
        else:
            self._base = Path("logs/storage")
            self._base.mkdir(parents=True, exist_ok=True)

    # ── Core read/write ───────────────────────────────────────────────────────

    def read(self, key: str) -> Any:
        """Read a JSON blob. Returns None if not found."""
        try:
            if self.backend == "gcs":
                blob = self._bucket.blob(key)
                if not blob.exists():
                    return None
                return json.loads(blob.download_as_text())
            else:
                path = self._base / key
                if not path.exists():
                    return None
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def write(self, key: str, data: Any):
        """Write a JSON blob."""
        try:
            payload = json.dumps(data, ensure_ascii=False, indent=2)
            if self.backend == "gcs":
                blob = self._bucket.blob(key)
                blob.upload_from_string(payload, content_type="application/json")
            else:
                path = self._base / key
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(payload, encoding="utf-8")
        except Exception as e:
            print(f"[StorageService] write error for {key}: {e}")

    def delete(self, key: str):
        """Delete a blob if it exists."""
        try:
            if self.backend == "gcs":
                blob = self._bucket.blob(key)
                if blob.exists():
                    blob.delete()
            else:
                path = self._base / key
                if path.exists():
                    path.unlink()
        except Exception as e:
            print(f"[StorageService] delete error for {key}: {e}")

    # ── Bookings ──────────────────────────────────────────────────────────────

    def save_booking(self, member_id: str, booking: dict):
        key  = f"bookings/{member_id}.json"
        data = self.read(key) or []
        sig  = f"{booking.get('provider_name')}|{booking.get('date')}|{booking.get('time_start')}"
        if not any(
            f"{b.get('provider_name')}|{b.get('date')}|{b.get('time_start')}" == sig
            for b in data
        ):
            booking["saved_at"] = datetime.utcnow().isoformat()
            data.append(booking)
        self.write(key, data)

    def get_bookings(self, member_id: str) -> list:
        return self.read(f"bookings/{member_id}.json") or []

    def get_last_booking(self, member_id: str) -> dict | None:
        bookings = self.get_bookings(member_id)
        return bookings[-1] if bookings else None

    # ── Conversation turns ────────────────────────────────────────────────────

    def save_turn(self, member_id: str, role: str, content: str):
        """Save a conversation turn. Triggers async compression if turns > threshold."""
        key  = f"conversations/{member_id}.json"
        data = self.read(key) or []
        data.append({
            "role":      role,
            "content":   content,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.write(key, data)

        # Trigger background compression if threshold exceeded
        if len(data) > _TURNS_COMPRESS_THRESHOLD:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._compress_turns_async(member_id, data))
            except RuntimeError:
                pass

    def get_history(self, member_id: str) -> list[dict]:
        """Returns last 20 turns as {role, content} dicts for agent context."""
        raw = self.read(f"conversations/{member_id}.json") or []
        return [{"role": t["role"], "content": t["content"]} for t in raw[-_TURNS_TO_KEEP:]]

    # ── History summary ───────────────────────────────────────────────────────

    def get_history_summary(self, member_id: str) -> str:
        """Returns a combined context string: long-term profile + recent summaries."""
        parts = []

        # Long-term profile (permanent, compressed)
        profile = self.read(f"long_term_profile/{member_id}.json")
        if profile and profile.get("summary"):
            parts.append(f"LONG-TERM PROFILE:\n{profile['summary']}")

        # Recent rolling summaries (last 12 months)
        summaries = self.read(f"history_summary/{member_id}.json") or []
        cutoff    = datetime.utcnow() - timedelta(days=365)
        recent    = [
            s for s in summaries
            if datetime.fromisoformat(s.get("created_at", "2000-01-01")) > cutoff
        ]
        if recent:
            summary_text = "\n".join(f"- {s['summary']}" for s in recent[-5:])
            parts.append(f"RECENT SESSION SUMMARIES:\n{summary_text}")

        return "\n\n".join(parts) if parts else ""

    def _save_summary_entry(self, member_id: str, summary_text: str):
        """Append a new summary entry. Triggers long-term compression if needed."""
        key      = f"history_summary/{member_id}.json"
        summaries = self.read(key) or []
        summaries.append({
            "summary":    summary_text,
            "created_at": datetime.utcnow().isoformat(),
        })
        self.write(key, summaries)

        # Trigger long-term compression for entries older than 12 months
        cutoff = datetime.utcnow() - timedelta(days=365)
        old    = [
            s for s in summaries
            if datetime.fromisoformat(s.get("created_at", "2000-01-01")) < cutoff
        ]
        if old:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._compress_long_term_async(member_id, old, summaries))
            except RuntimeError:
                pass

    # ── Async compression (background, non-blocking) ──────────────────────────

    async def _compress_turns_async(self, member_id: str, all_turns: list):
        """
        Background task: compress oldest turns into a summary entry.
        Keeps latest _TURNS_TO_KEEP turns, compresses _TURNS_TO_COMPRESS oldest.
        """
        try:
            to_compress = all_turns[:_TURNS_TO_COMPRESS]
            to_keep     = all_turns[_TURNS_TO_COMPRESS:]

            # Build text for LLM to summarize
            turns_text = "\n".join(
                f"{t['role'].upper()}: {t['content'][:200]}"
                for t in to_compress
            )

            summary = await _summarize_turns(turns_text, member_id)

            # Save summary entry
            self._save_summary_entry(member_id, summary)

            # Write back only the turns to keep
            self.write(f"conversations/{member_id}.json", to_keep)

            print(f"[StorageService] Compressed {len(to_compress)} turns for {member_id}")

        except Exception as e:
            print(f"[StorageService] Compression error for {member_id}: {e}")

    async def _compress_long_term_async(
        self, member_id: str, old_summaries: list, all_summaries: list
    ):
        """
        Background task: merge old summary entries into the long-term profile.
        Deletes old entries after merging.
        """
        try:
            old_text = "\n".join(f"- {s['summary']}" for s in old_summaries)

            # Get existing long-term profile
            existing = self.read(f"long_term_profile/{member_id}.json") or {}
            existing_profile = existing.get("summary", "")

            combined = await _merge_into_profile(old_text, existing_profile, member_id)

            # Save updated long-term profile
            self.write(f"long_term_profile/{member_id}.json", {
                "summary":    combined,
                "updated_at": datetime.utcnow().isoformat(),
            })

            # Remove old entries from summaries, keep recent ones
            cutoff  = datetime.utcnow() - timedelta(days=365)
            kept    = [
                s for s in all_summaries
                if datetime.fromisoformat(s.get("created_at", "2000-01-01")) >= cutoff
            ]
            self.write(f"history_summary/{member_id}.json", kept)

            print(f"[StorageService] Merged {len(old_summaries)} old summaries into long-term profile for {member_id}")

        except Exception as e:
            print(f"[StorageService] Long-term compression error for {member_id}: {e}")

    # ── Notifications ─────────────────────────────────────────────────────────

    def save_notification(self, notification: dict):
        key  = "notifications/all.json"
        data = self.read(key) or []
        notification["created_at"] = datetime.utcnow().isoformat()
        notification["status"]     = "sent"
        data.append(notification)
        self.write(key, data)
        return notification

    def get_notifications(self, member_id: str) -> list:
        all_notifs = self.read("notifications/all.json") or []
        return [n for n in all_notifs if n.get("member_id") == member_id]

    # ── Plan change ───────────────────────────────────────────────────────────

    def save_plan_change(self, member_id: str, previous_plan: str, previous_plan_id: str, new_plan: str = "", new_plan_id: str = ""):
        self.write(f"plan_change/{member_id}.json", {
            "previous_plan":    previous_plan,
            "previous_plan_id": previous_plan_id,
            "new_plan":         new_plan,
            "new_plan_id":      new_plan_id,
            "changed_at":       datetime.utcnow().isoformat(),
        })

    def get_and_clear_plan_change(self, member_id: str) -> dict | None:
        """
        Called by _build_system_prompt to inject the one-time plan-change context block.

        Lifecycle:
          • File exists, no payer_decision yet → return data and mark _initial_shown=True
            (do NOT delete — payer still needs to see it to approve/decline)
          • File has payer_decision (payer decided before member's first login) → return data and delete
          • File has _initial_shown=True already → skip (return None, don't inject twice)
        """
        key  = f"plan_change/{member_id}.json"
        data = self.read(key)
        if not data:
            return None
        # If payer already decided: inject once then delete
        if data.get("payer_decision"):
            # This case is handled by _build_proactive_block, not here — skip
            return None
        # Already shown on a previous login — don't show again
        if data.get("_initial_shown"):
            return None
        # First time: mark as shown, keep file so payer can act on it
        data["_initial_shown"] = True
        self.write(key, data)
        return data

    def update_plan(self, member_id: str, new_plan: str, new_plan_id: str):
        self.write(f"plan_override/{member_id}.json", {
            "insurance_plan":    new_plan,
            "insurance_plan_id": new_plan_id,
        })

    def get_plan_override(self, member_id: str) -> dict | None:
        return self.read(f"plan_override/{member_id}.json")

    # ── MRI Prescription ─────────────────────────────────────────────────────

    def get_mri_prescription(self, member_id: str) -> dict | None:
        """Always reads from local file regardless of backend."""
        path = Path(f"logs/storage/mri_prescription/{member_id}.json")
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def update_mri_prescription(self, member_id: str, data: dict):
        """Always writes to local file regardless of backend."""
        path = Path(f"logs/storage/mri_prescription/{member_id}.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── Prior Authorization ───────────────────────────────────────────────────

    def get_prior_auth(self, member_id: str) -> dict | None:
        """Always reads from local file for easy demo tweaking."""
        path = Path(f"logs/storage/prior_auth/{member_id}.json")
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def save_prior_auth(self, member_id: str, data: dict):
        """Always writes to local file for easy demo tweaking."""
        path = Path(f"logs/storage/prior_auth/{member_id}.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def toggle_prior_auth_status(self, member_id: str) -> str:
        """Cycle prior auth status: none -> pending -> approved -> pending.
        Creates the file with status=pending if it does not exist."""
        path = Path(f"logs/storage/prior_auth/{member_id}.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.utcnow()

        if not path.exists():
            data = {
                "status":     "pending",
                "created_at": now.isoformat(),
            }
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return "pending"

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}

        current = data.get("status", "none")
        if current == "none":
            data["status"]         = "pending"
            data["submitted_date"] = now.strftime("%Y-%m-%d")
            data["approved_date"]  = None
            data["valid_through"]  = None
        elif current == "pending":
            data["status"]         = "approved"
            data["approved_date"]  = now.strftime("%Y-%m-%d")
            data["valid_through"]  = (now + timedelta(days=90)).strftime("%Y-%m-%d")
        else:
            data["status"]         = "pending"
            data["approved_date"]  = None
            data["valid_through"]  = None

        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data["status"]

    # ── PCP Change ────────────────────────────────────────────────────────────

    def save_pcp_change_request(self, member_id: str, request: dict):
        path = Path(f"logs/storage/pcp_change/{member_id}.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        except Exception:
            data = []
        request["requested_at"] = datetime.utcnow().isoformat()
        request["status"]       = "pending"
        data.append(request)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def update_pcp(self, member_id: str, new_pcp: dict):
        """Persist updated PCP so it survives session restarts."""
        path = Path(f"logs/storage/pcp_change/override_{member_id}.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"assigned_pcp": new_pcp, "updated_at": datetime.utcnow().isoformat()},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_pcp_override(self, member_id: str) -> dict | None:
        path = Path(f"logs/storage/pcp_change/override_{member_id}.json")
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("assigned_pcp")
        except Exception:
            return None

    # ── Referral ──────────────────────────────────────────────────────────────

    def get_referral(self, member_id: str) -> dict | None:
        """Read referral record — written by provider dashboard, read by agent."""
        path = Path(f"logs/storage/referral/{member_id}.json")
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def save_referral(self, member_id: str, data: dict):
        path = Path(f"logs/storage/referral/{member_id}.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def check_and_complete_pcp_change(self, member_id: str) -> dict | None:
        """
        Check if any pending PCP change has passed the processing window.
        Demo mode: 35 seconds. Returns the completed request or None.
        """
        path = Path(f"logs/storage/pcp_change/{member_id}.json")
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

        PROCESSING_SECONDS = 35
        now     = datetime.utcnow()
        updated = False
        result  = None

        for req in data:
            if req.get("status") != "pending":
                continue
            try:
                requested_at = datetime.fromisoformat(req["requested_at"])
            except Exception:
                continue
            if (now - requested_at).total_seconds() >= PROCESSING_SECONDS:
                req["status"]       = "completed"
                req["completed_at"] = now.isoformat()
                updated = True
                result  = req

        if updated:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        return result

# ── LLM helpers for compression (called only during background tasks) ─────────

async def _summarize_turns(turns_text: str, member_id: str) -> str:
    """Use LLM to compress conversation turns into a concise summary."""
    try:
        from app.services.llm_service import LLMService
        llm    = LLMService()
        prompt = f"""Summarize this healthcare conversation into 2-3 sentences.
Focus on: symptoms discussed, doctors found, appointments booked, conditions mentioned, decisions made.
Be factual and concise. No filler words.

Conversation:
{turns_text[:3000]}

Summary:"""
        result = llm.generate_text(prompt).strip()
        return result if result else "Session with healthcare assistant."
    except Exception:
        return "Session with healthcare assistant."


async def _merge_into_profile(old_summaries: str, existing_profile: str, member_id: str) -> str:
    """Merge old summaries into the long-term profile."""
    try:
        from app.services.llm_service import LLMService
        llm    = LLMService()
        prompt = f"""You are updating a member's long-term health profile.
Merge the existing profile with the new session summaries into a single concise paragraph (max 150 words).
Keep: conditions, regular doctors, medications, important procedures, recurring issues.
Remove: one-time minor issues, outdated information.

Existing profile:
{existing_profile or '(none yet)'}

New session summaries to merge:
{old_summaries[:2000]}

Updated profile (max 150 words):"""
        result = llm.generate_text(prompt).strip()
        return result if result else existing_profile or old_summaries[:500]
    except Exception:
        return existing_profile or old_summaries[:500]


# Singleton
storage = StorageService()

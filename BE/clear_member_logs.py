"""
clear_member_logs.py
--------------------
Removes all stored logs and session data for a specific member —
from BOTH the local filesystem AND the GCS bucket (if configured).

Usage:
  python clear_member_logs.py MEM-10003
  python clear_member_logs.py MEM-10003 --dry-run
  python clear_member_logs.py --all          (clears ALL members — prompts for confirmation)

Environment variables (same as the app):
  STORAGE_BACKEND    = local | gcs   (default: gcs)
  GCS_BUCKET_NAME    = <bucket name> (default: provider_search_applicationstore)
  GCP_PROJECT_ID     = <project id>
"""

import argparse
import json
import os
import sys
from pathlib import Path

# ── Load .env so we pick up the same settings the app uses ───────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed — rely on real env vars

# ── Config (mirrors app/config.py) ───────────────────────────────────────────
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "gcs")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "provider_search_applicationstore")
GCP_PROJECT_ID  = os.getenv("GCP_PROJECT_ID")

# ── Root paths ────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).resolve().parent
LOGS_DIR  = BASE_DIR / "logs"
STORE_DIR = LOGS_DIR / "storage"

# ── All storage sub-folders that use {member_id}.json ────────────────────────
STORAGE_SUBDIRS = [
    "bookings",
    "conversations",
    "history_summary",
    "long_term_profile",
    "mri_prescription",
    "prior_auth",
    "referral",
    "pcp_changes",
    "plan_change",
    "notifications",
    "appointments",
]

# ── Conversation/memory folders (local only, not stored in GCS) ───────────────
CONVERSATION_DIRS = [
    LOGS_DIR / "conversation" / "json",
    LOGS_DIR / "conversation" / "txt",
    LOGS_DIR / "health_memory",
    LOGS_DIR / "explainability",
]


# ─────────────────────────────────────────────────────────────────────────────
# GCS helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_gcs_bucket():
    """Return a GCS bucket object, or None if unavailable."""
    try:
        from google.cloud import storage as gcs
        client = gcs.Client(project=GCP_PROJECT_ID)
        return client.bucket(GCS_BUCKET_NAME)
    except Exception as e:
        print(f"  [GCS] Could not connect to bucket '{GCS_BUCKET_NAME}': {e}")
        return None


def _gcs_delete_blob(bucket, key: str, dry_run: bool) -> bool:
    """Delete a single GCS blob. Returns True if it existed."""
    try:
        blob = bucket.blob(key)
        if blob.exists():
            if dry_run:
                print(f"  [GCS DRY-RUN] Would delete: gs://{GCS_BUCKET_NAME}/{key}")
            else:
                blob.delete()
                print(f"  ✓ [GCS] Deleted: gs://{GCS_BUCKET_NAME}/{key}")
            return True
    except Exception as e:
        print(f"  [GCS] Error deleting {key}: {e}")
    return False


def _gcs_remove_member_from_array_blob(bucket, key: str, member_id: str, dry_run: bool) -> bool:
    """
    For GCS blobs that contain a JSON array, remove entries matching member_id.
    Returns True if the blob was modified.
    """
    try:
        blob = bucket.blob(key)
        if not blob.exists():
            return False
        data = json.loads(blob.download_as_text())
        if not isinstance(data, list):
            return False
        original_count = len(data)
        filtered = [
            item for item in data
            if item.get("member_id") != member_id
            and item.get("user_id") != member_id
            and item.get("memberId") != member_id
        ]
        if len(filtered) == original_count:
            return False
        removed = original_count - len(filtered)
        if dry_run:
            print(f"  [GCS DRY-RUN] Would remove {removed} entry/entries from: gs://{GCS_BUCKET_NAME}/{key}")
        else:
            blob.upload_from_string(
                json.dumps(filtered, indent=2),
                content_type="application/json"
            )
            print(f"  ✓ [GCS] Removed {removed} entry/entries from: gs://{GCS_BUCKET_NAME}/{key}")
        return True
    except Exception as e:
        print(f"  [GCS] Error patching {key}: {e}")
        return False


def _gcs_list_member_blobs(bucket, member_id: str) -> list:
    """List all blobs in the bucket whose name contains the member_id."""
    try:
        return [b for b in bucket.list_blobs() if member_id in b.name]
    except Exception as e:
        print(f"  [GCS] Could not list blobs: {e}")
        return []


def _gcs_list_all_member_ids(bucket) -> set:
    """Scan all blobs under storage subdirs and extract member IDs from filenames."""
    member_ids = set()
    try:
        for blob in bucket.list_blobs():
            parts = blob.name.split("/")
            if len(parts) >= 2 and parts[0] in STORAGE_SUBDIRS:
                stem = parts[-1].replace(".json", "")
                if stem.startswith("MEM-") or stem.startswith("mem-"):
                    member_ids.add(stem)
    except Exception as e:
        print(f"  [GCS] Could not scan bucket: {e}")
    return member_ids


# ─────────────────────────────────────────────────────────────────────────────
# Local helpers
# ─────────────────────────────────────────────────────────────────────────────

def _local_delete(path: Path, dry_run: bool) -> bool:
    if path.exists():
        if dry_run:
            print(f"  [LOCAL DRY-RUN] Would delete: {path}")
        else:
            path.unlink()
            print(f"  ✓ [LOCAL] Deleted: {path}")
        return True
    return False


def _local_remove_member_from_json_array(path: Path, member_id: str, dry_run: bool) -> bool:
    if not path.exists():
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return False
    if not isinstance(data, list):
        return False
    original_count = len(data)
    filtered = [
        item for item in data
        if item.get("member_id") != member_id
        and item.get("user_id") != member_id
        and item.get("memberId") != member_id
    ]
    if len(filtered) == original_count:
        return False
    removed = original_count - len(filtered)
    if dry_run:
        print(f"  [LOCAL DRY-RUN] Would remove {removed} entry/entries from: {path}")
    else:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(filtered, f, indent=2)
        print(f"  ✓ [LOCAL] Removed {removed} entry/entries from: {path}")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Main clear logic
# ─────────────────────────────────────────────────────────────────────────────

def clear_member_local(member_id: str, dry_run: bool) -> int:
    """Clear all local log files for a member. Returns count of items removed."""
    deleted = 0

    # Per-member JSON files in storage subdirs
    for subdir in STORAGE_SUBDIRS:
        target = STORE_DIR / subdir / f"{member_id}.json"
        if _local_delete(target, dry_run):
            deleted += 1

    # notifications/all.json — remove entries matching member
    notif_all = STORE_DIR / "notifications" / "all.json"
    if _local_remove_member_from_json_array(notif_all, member_id, dry_run):
        deleted += 1

    # appointments.json (root-level)
    appt_root = LOGS_DIR / "appointments.json"
    if _local_remove_member_from_json_array(appt_root, member_id, dry_run):
        deleted += 1

    # Audit logs
    audit_dir = LOGS_DIR / "audit"
    if audit_dir.exists():
        for audit_file in sorted(audit_dir.glob("audit_*.json")):
            if _local_remove_member_from_json_array(audit_file, member_id, dry_run):
                deleted += 1

    # Conversation + memory files
    for conv_dir in CONVERSATION_DIRS:
        if conv_dir.exists():
            for pattern in [f"{member_id}*.json", f"{member_id}*.txt", f"{member_id}*"]:
                for f in conv_dir.glob(pattern):
                    if _local_delete(Path(f), dry_run):
                        deleted += 1

    # Wildcard scan under logs/
    seen = {STORE_DIR / s / f"{member_id}.json" for s in STORAGE_SUBDIRS}
    for f in LOGS_DIR.rglob(f"{member_id}*"):
        if f.is_file() and f not in seen:
            if _local_delete(f, dry_run):
                deleted += 1

    return deleted


def clear_member_gcs(member_id: str, dry_run: bool, bucket) -> int:
    """Clear all GCS blobs for a member. Returns count of items removed."""
    deleted = 0

    # Per-member blobs for each storage subdir
    for subdir in STORAGE_SUBDIRS:
        key = f"{subdir}/{member_id}.json"
        if _gcs_delete_blob(bucket, key, dry_run):
            deleted += 1

    # notifications/all.json — filter out member entries
    if _gcs_remove_member_from_array_blob(bucket, "notifications/all.json", member_id, dry_run):
        deleted += 1

    # Any other blobs whose name contains the member_id (catchall)
    for blob in _gcs_list_member_blobs(bucket, member_id):
        # Skip keys already handled above to avoid double-counting
        handled = {f"{s}/{member_id}.json" for s in STORAGE_SUBDIRS} | {"notifications/all.json"}
        if blob.name not in handled:
            if dry_run:
                print(f"  [GCS DRY-RUN] Would delete: gs://{GCS_BUCKET_NAME}/{blob.name}")
            else:
                try:
                    blob.delete()
                    print(f"  ✓ [GCS] Deleted: gs://{GCS_BUCKET_NAME}/{blob.name}")
                except Exception as e:
                    print(f"  [GCS] Error deleting {blob.name}: {e}")
            deleted += 1

    return deleted


def clear_member(member_id: str, dry_run: bool = False):
    print(f"\n{'[DRY-RUN] ' if dry_run else ''}Clearing logs for member: {member_id}\n")
    total = 0

    # ── Local ─────────────────────────────────────────────────────────────────
    print("── Local filesystem ──")
    local_count = clear_member_local(member_id, dry_run)
    if local_count == 0:
        print("  (nothing found locally)")
    total += local_count

    # ── GCS ───────────────────────────────────────────────────────────────────
    print("\n── GCS bucket ──")
    bucket = _get_gcs_bucket()
    if bucket:
        gcs_count = clear_member_gcs(member_id, dry_run, bucket)
        if gcs_count == 0:
            print("  (nothing found in GCS)")
        total += gcs_count
    else:
        print("  (skipped — GCS not available)")

    print(f"\n{'Would remove' if dry_run else 'Removed'} {total} file(s)/entry/entries total for {member_id}.")


def clear_all_members(dry_run: bool = False):
    """Find every member ID across local storage + GCS and clear them all."""
    member_ids = set()

    # Collect from local
    for subdir in STORAGE_SUBDIRS:
        d = STORE_DIR / subdir
        if d.exists():
            for f in d.glob("*.json"):
                member_ids.add(f.stem)

    # Collect from GCS
    bucket = _get_gcs_bucket()
    if bucket:
        member_ids |= _gcs_list_all_member_ids(bucket)

    if not member_ids:
        print("No member data found.")
        return

    print(f"Found {len(member_ids)} member(s): {', '.join(sorted(member_ids))}")
    confirm = input("Clear ALL members? This cannot be undone. Type YES to confirm: ")
    if confirm.strip() != "YES":
        print("Aborted.")
        return

    for mid in sorted(member_ids):
        clear_member(mid, dry_run)


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Clear all stored logs for a member — locally AND in GCS."
    )
    parser.add_argument(
        "member_id",
        nargs="?",
        help="Member ID to clear (e.g. MEM-10003). Omit if using --all.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be deleted without actually deleting anything.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Clear logs for ALL members (prompts for confirmation).",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Only clear local filesystem logs, skip GCS.",
    )
    parser.add_argument(
        "--gcs-only",
        action="store_true",
        help="Only clear GCS bucket blobs, skip local files.",
    )

    args = parser.parse_args()

    # Override backend based on flags
    if args.local_only:
        STORAGE_BACKEND = "local"
    if args.gcs_only:
        STORAGE_BACKEND = "gcs"

    if args.all:
        clear_all_members(dry_run=args.dry_run)
    elif args.member_id:
        # If local-only / gcs-only flags are set, run only the relevant section
        if args.local_only:
            print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}Clearing LOCAL logs for: {args.member_id}\n")
            c = clear_member_local(args.member_id, args.dry_run)
            print(f"\n{'Would remove' if args.dry_run else 'Removed'} {c} item(s).")
        elif args.gcs_only:
            print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}Clearing GCS logs for: {args.member_id}\n")
            b = _get_gcs_bucket()
            if b:
                c = clear_member_gcs(args.member_id, args.dry_run, b)
                print(f"\n{'Would remove' if args.dry_run else 'Removed'} {c} item(s).")
            else:
                print("GCS not available.")
        else:
            clear_member(args.member_id, dry_run=args.dry_run)
    else:
        parser.print_help()
        sys.exit(1)

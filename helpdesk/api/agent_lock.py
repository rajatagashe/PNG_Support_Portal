# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _
from helpdesk.utils import agent_only

LOCK_TTL_SECONDS = 120


def _get_lock_cache_key(ticket_id: str) -> str:
    return f"hd_ticket_lock:{ticket_id}"


def _clear_local_cache(cache, key: str):
    """Evict in-memory local cache entry so subsequent get_value calls hit Redis directly."""
    full_key = cache.make_key(key)
    if hasattr(frappe, "local") and hasattr(frappe.local, "cache"):
        frappe.local.cache.pop(full_key, None)


@frappe.whitelist()
@agent_only
def acquire_ticket_lock(ticket_id: str, force: bool = False) -> dict:
    """Acquire an active edit/reply lock on a ticket to prevent agent collision."""
    if not ticket_id or not frappe.db.exists("HD Ticket", ticket_id):
        frappe.throw(_("Ticket not found"), frappe.DoesNotExistError)

    cache = frappe.cache
    key = _get_lock_cache_key(ticket_id)
    raw_lock = cache.get_value(key, expires=True)

    user = frappe.session.user
    agent_name = frappe.db.get_value("HD Agent", {"user": user}, "agent_name") or frappe.utils.get_fullname(user) or user

    lock_payload = {
        "user": user,
        "agent_name": agent_name,
        "ticket": ticket_id,
        "locked_at": frappe.utils.now(),
    }

    if raw_lock:
        current_lock = json.loads(raw_lock) if isinstance(raw_lock, str) else raw_lock
        # If already locked by current user, renew TTL
        if current_lock.get("user") == user:
            cache.set_value(key, json.dumps(lock_payload), expires_in_sec=LOCK_TTL_SECONDS)
            _clear_local_cache(cache, key)
            return {"is_locked": False, "acquired": True, "renewed": True, "expires_in": LOCK_TTL_SECONDS}

        # Locked by another agent
        if not force:
            return {
                "is_locked": True,
                "acquired": False,
                "locked_by": current_lock.get("agent_name"),
                "locked_by_user": current_lock.get("user"),
                "locked_at": current_lock.get("locked_at"),
            }

        # Force takeover
        cache.set_value(key, json.dumps(lock_payload), expires_in_sec=LOCK_TTL_SECONDS)
        _clear_local_cache(cache, key)
        frappe.publish_realtime(
            "helpdesk:ticket_lock_taken_over",
            {"ticket": ticket_id, "taken_by": agent_name, "user": user},
            doctype="HD Ticket",
            docname=ticket_id,
        )
        return {"is_locked": False, "acquired": True, "taken_over": True, "expires_in": LOCK_TTL_SECONDS}

    # Brand new lock
    cache.set_value(key, json.dumps(lock_payload), expires_in_sec=LOCK_TTL_SECONDS)
    _clear_local_cache(cache, key)
    frappe.publish_realtime(
        "helpdesk:ticket_locked",
        {"ticket": ticket_id, "locked_by": agent_name, "user": user},
        doctype="HD Ticket",
        docname=ticket_id,
    )
    return {"is_locked": False, "acquired": True, "expires_in": LOCK_TTL_SECONDS}


@frappe.whitelist()
@agent_only
def get_ticket_lock(ticket_id: str) -> dict:
    """Check the lock state of a ticket."""
    if not ticket_id:
        return {"is_locked": False}

    cache = frappe.cache
    key = _get_lock_cache_key(ticket_id)
    raw_lock = cache.get_value(key, expires=True)

    if not raw_lock:
        return {"is_locked": False}

    current_lock = json.loads(raw_lock) if isinstance(raw_lock, str) else raw_lock
    is_self = current_lock.get("user") == frappe.session.user

    return {
        "is_locked": True,
        "is_self": is_self,
        "locked_by": current_lock.get("agent_name"),
        "locked_by_user": current_lock.get("user"),
        "locked_at": current_lock.get("locked_at"),
    }


@frappe.whitelist()
@agent_only
def release_ticket_lock(ticket_id: str) -> dict:
    """Release an active edit lock on a ticket."""
    if not ticket_id:
        return {"released": False}

    cache = frappe.cache
    key = _get_lock_cache_key(ticket_id)
    raw_lock = cache.get_value(key, expires=True)

    if not raw_lock:
        return {"released": True}

    current_lock = json.loads(raw_lock) if isinstance(raw_lock, str) else raw_lock
    user = frappe.session.user
    is_admin = user == "Administrator" or "System Manager" in frappe.get_roles(user)

    if current_lock.get("user") == user or is_admin:
        cache.delete_value(key)
        _clear_local_cache(cache, key)
        frappe.publish_realtime(
            "helpdesk:ticket_unlocked",
            {"ticket": ticket_id, "released_by": user},
            doctype="HD Ticket",
            docname=ticket_id,
        )
        return {"released": True}

    return {"released": False, "error": _("Cannot release lock held by another agent")}

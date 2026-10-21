# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.automation.doctype.assignment_rule.assignment_rule import AssignmentRule


def get_agents_by_category(category: str) -> set[str]:
    """User ids of HD Agents whose current status falls under the given category."""
    statuses = frappe.get_all(
        "HD Agent Status",
        filters={"category": category},
        pluck="name",
    )
    if not statuses:
        return set()
    return set(
        frappe.get_all(
            "HD Agent",
            filters={"availability": ["in", statuses]},
            pluck="user",
        )
    )


def get_agents_with_skills(required_skills: list[str]) -> set[str]:
    """Return user IDs of HD Agents who possess all specified required skills."""
    if not required_skills:
        return set()

    agent_skills = frappe.get_all(
        "HD Agent Skill",
        filters={"skill": ["in", required_skills]},
        fields=["parent", "skill"],
    )
    agent_skill_map: dict[str, set[str]] = {}
    for row in agent_skills:
        agent_skill_map.setdefault(row.parent, set()).add(row.skill)

    req_set = set(required_skills)
    qualified_agent_names = [
        agent_name for agent_name, skills in agent_skill_map.items() if req_set.issubset(skills)
    ]
    if not qualified_agent_names:
        # Fallback to agents matching at least one skill
        qualified_agent_names = list(agent_skill_map.keys())

    if not qualified_agent_names:
        return set()

    return set(
        frappe.get_all(
            "HD Agent",
            filters={"name": ["in", qualified_agent_names], "is_active": 1},
            pluck="user",
        )
    )


def get_agent_open_ticket_count(user: str) -> int:
    """Return the number of unresolved tickets currently assigned to a user."""
    return frappe.db.count(
        "HD Ticket",
        {
            "_assign": ["like", f"%{user}%"],
            "status_category": ["!=", "Resolved"],
        },
    )


def is_agent_under_capacity(user: str) -> bool:
    """Check if an agent has active open ticket workload below their configured max capacity."""
    agent_doc = frappe.db.get_value(
        "HD Agent", {"user": user}, ["max_concurrent_tickets"], as_dict=True
    )
    if not agent_doc or not agent_doc.get("max_concurrent_tickets"):
        return True

    max_capacity = agent_doc.get("max_concurrent_tickets")
    current_count = get_agent_open_ticket_count(user)
    return current_count < max_capacity


class HelpdeskAssignmentRule(AssignmentRule):
    def get_user(self, doc):
        """
        Override get_user method with availability tiers, skill-based matching, and capacity caps:
        1. Skill-Based Filter: Only agents matching required skills are considered.
        2. Capacity Filter: Agents who have reached their max concurrent ticket cap are skipped.
        3. Availability Tier: Active → Away → Unavailable (as last resort so ticket is never left unassigned).
        """
        # Determine pool fieldname
        if self.rule == "Weighted Distribution":
            user_pool_fieldname = "weighted_users"
        elif self.rule in ("Round Robin", "Load Balancing"):
            user_pool_fieldname = "users"
        else:
            return super().get_user(doc)

        original_pool = list(getattr(self, user_pool_fieldname) or [])
        if not original_pool:
            return super().get_user(doc)

        pool = original_pool

        # 1. Skill Matching Filter
        required_skills = [
            row.skill for row in doc.get("skills", []) if getattr(row, "skill", None)
        ]
        if required_skills:
            skilled_users = get_agents_with_skills(required_skills)
            skilled_pool = [u for u in pool if u.user in skilled_users]
            if skilled_pool:
                pool = skilled_pool

        # VIP / Senior Routing Filter
        is_vip = (
            getattr(getattr(doc, "flags", None), "is_vip_ticket", False)
            or getattr(getattr(doc, "flags", None), "require_senior_agent", False)
            or (doc.get("customer") and frappe.db.get_value("HD Customer", doc.customer, "is_vip"))
            or ("vip-cgd" in (doc.get("_user_tags") or ""))
        )
        if is_vip:
            senior_roles = {"HD Tier 2 Agent", "HD Team Lead", "Agent Manager"}
            senior_users = set(
                frappe.get_all(
                    "Has Role",
                    filters={"role": ["in", list(senior_roles)]},
                    pluck="parent",
                )
            )
            senior_pool = [u for u in pool if u.user in senior_users]
            if senior_pool:
                pool = senior_pool

        # 2. Capacity Cap Filter
        under_capacity_pool = [u for u in pool if is_agent_under_capacity(u.user)]
        if under_capacity_pool:
            pool = under_capacity_pool
        else:
            # If all are at capacity, pick the least loaded agent in the pool
            pool.sort(key=lambda u: get_agent_open_ticket_count(u.user))
            pool = [pool[0]]

        # 3. Availability Tiers: Active → Away → Unavailable
        away = get_agents_by_category("Away")
        unavailable = get_agents_by_category("Unavailable")

        active_only = [u for u in pool if u.user not in away and u.user not in unavailable]
        not_unavailable = [u for u in pool if u.user not in unavailable]

        if active_only:
            preferred_pool = active_only
        elif not_unavailable:
            preferred_pool = not_unavailable
        else:
            preferred_pool = pool

        setattr(self, user_pool_fieldname, preferred_pool)
        try:
            return super().get_user(doc)
        finally:
            setattr(self, user_pool_fieldname, original_pool)

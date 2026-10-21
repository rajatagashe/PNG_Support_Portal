# MyPNG Support Desk & Frappe Helpdesk: Architecture, Requirements & Comprehensive Enhancement Plan

> **Document Version**: 2.0  
> **Last Updated**: 2026-10-16  
> **Target Platform**: Frappe Helpdesk (Frappe Framework / Python / MariaDB / Redis / Vue 3 / Vite)  
> **Context**: Consolidation of Zendesk-grade enterprise ticketing capabilities with the **MyPNG Support Desk** multi-CGD (City Gas Distribution) project requirements.

---

## 1. Executive Summary & Vision

The objective of this project is to build and maintain an enterprise-grade, self-hosted customer support and helpdesk ticketing system. The platform serves two converging objectives:

1. **MyPNG Support Desk Requirements**: A secure, isolated ticketing hub receiving customer queries from multiple **CGD entities** (e.g., BPCL, IGL, GAIL, and others) into a shared mailbox, strictly isolating tenant data while providing unified internal agent operations.
2. **Zendesk-Grade Helpdesk Evolution**: Incrementally upgrading Frappe Helpdesk with advanced helpdesk capabilities—including visual event-driven triggers, time-based automations, skill-based capacity routing, agent collision prevention, side conversations, and comprehensive CSAT reporting.

```
                           ┌─────────────────────────────────────────────────────────┐
                           │          Client Layer (Vue 3 / TypeScript SPA)          │
                           │  - Agent Desk (/helpdesk/tickets, /home, /analytics)    │
                           │  - CGD Customer Portal (/helpdesk/my-tickets, /kb)      │
                           │  - Real-time Collaboration (Socket.IO Presence/Typing)  │
                           └────────────────────────────┬────────────────────────────┘
                                                        │ HTTPS / REST / WebSockets
                                                        ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   Frappe Application Layer (Python)                                    │
│                                                                                                        │
│  [Multi-Tenant CGD Gate]           [Core Controller Logic]               [Workflow & Automation]       │
│  - CustomInboundMail (Deduplication)- HD Ticket (hd_ticket.py)            - Assignment Rule Routing     │
│  - Customer & Domain Mapping       - HD Team & Agent Queues              - SLA Clock & Auto-Close      │
│  - Document Permission Queries     - Comment Security Shield             - Dynamic Email Notifications │
└───────────────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                                        │
                   ┌────────────────────────────────────┼────────────────────────────────────┐
                   ▼                                    ▼                                    ▼
       ┌────────────────────────┐           ┌────────────────────────┐           ┌────────────────────────┐
       │   MariaDB Database     │           │    Redis In-Memory     │           │    Full-Text Search    │
       │ - Structured DocTypes  │           │ - Cache & Worker Queue │           │ - RediSearch / SQLite  │
       │ - Strict RBAC Queries  │           │ - Realtime Pub/Sub     │           │ - Tenant Pre-filtering │
       └────────────────────────┘           └────────────────────────┘           └────────────────────────┘
```

---

## 2. Master Feature & Requirements Implementation Status

The table below provides a full inventory of requirements from both the **MyPNG Project Overview** and the **Zendesk Benchmark Specification**, clearly distinguishing between what is already built and what needs development.

| # | Requirement / Feature | Category | Source | Current Status | Codebase Location / Implementation Details |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **1** | **Email Ingestion to Ticket** (`MAIL-01`) | Inbound Email | MyPNG / Core | **IMPLEMENTED** | `helpdesk/overrides/email_account.py` (`CustomEmailAccount`, `CustomInboundMail`). Converts emails into `HD Ticket` and `Communication`. |
| **2** | **Reply Thread Stitching** (`MAIL-02`) | Inbound Email | MyPNG / Core | **IMPLEMENTED** | `helpdesk/overrides/email_account.py`. Uses `In-Reply-To` and walks back through `References` headers to attach replies to existing tickets. |
| **3** | **Duplicate Email Deduplication** (`MAIL-03`) | Inbound Email | MyPNG Finding | **IMPLEMENTED** | `frappe.email.receive.InboundMail.process()` calls `is_exist_in_system()`, deduplicating via `Message-ID`. *(Note: Successfully overcomes Zammad's flaw).* |
| **4** | **Contact-to-Customer Mapping** | Inbound Email | MyPNG | **IMPLEMENTED** | `hd_ticket.py` (`set_contact`, `set_customer`). Automatically assigns customer if the sender's `Contact` is linked to an `HD Customer`. |
| **5** | **Domain-Based Auto Customer Mapping** | Inbound Email | MyPNG Gap | **IMPLEMENTED** | `hd_domain_mapping.py`, `hd_ticket.py` (`map_customer_from_domain`), `hd_settings.json`. Maps sender email domain against `HD Domain Mapping` and fallback `HD Customer.domain`, linking contacts and defaulting teams. |
| **6** | **Unknown Sender Triage** (`MAIL-04`) | Inbound Email | MyPNG | **IMPLEMENTED** | `hd_ticket.py` (`handle_unclassified_ticket`, `apply_unclassified_tag`). Unmapped tickets route to configurable `unclassified_team` and receive `unclassified-cgd` tag. |
| **7** | **Authorized Sender Identity** (`MAIL-05`) | Outbound Email | MyPNG | **IMPLEMENTED** *(Config)* | `helpdesk/helpdesk/utils/email.py` and `HDTicket.reply_via_agent()`. Outbound replies use default outgoing email account (e.g., "My Support PNG"). |
| **8** | **Strict Cross-CGD URL Isolation** (`SEC-01`) | Security / RBAC | MyPNG | **IMPLEMENTED** | `hd_ticket.py` (`has_permission`). Denies direct ticket URL access if user does not belong to the ticket's customer entity. |
| **9** | **Cross-CGD Search Isolation** (`SEC-02`) | Security / Search | MyPNG | **IMPLEMENTED** | `helpdesk/search_sqlite.py` (`_get_accessible_tickets`). Search results pre-filtered by `frappe.get_list('HD Ticket')`, preventing search leakage. |
| **10** | **Cross-CGD Attachment Access** (`SEC-03`) | Security / Files | MyPNG | **IMPLEMENTED** | Frappe Framework file permission checks inherit parent ticket permissions; unauthorized users cannot download attachments. |
| **11** | **Invitation-Based User Onboarding** | Security / Portal | MyPNG / Core | **IMPLEMENTED** | `helpdesk/helpdesk/hooks/user_invitation.py`. Admin/Agent invites customer contacts with roles `HD Customer` or `HD Customer Manager`. |
| **12** | **Portal Self-Registration Approval UI** (`SEC-04`) | Security / Portal | MyPNG Gap | **IMPLEMENTED** | `hd_customer_signup_request.py`, `customer_signup.py`, and `SignupRequestsConfig.vue`. Public registration submission, approval lifecycle provisioning user/contact, and manager review UI. |
| **13** | **Internal Notes Shielding** (`SEC-05`) | Security / Notes | MyPNG / Zendesk | **IMPLEMENTED** | `helpdesk/extends/comment.py` (`can_see_ticket_comments`). Internal notes are restricted strictly to agents (`is_agent(user)`). |
| **14** | **Mailbox Disconnect & Backlog Sync** (`OPS-01`)| Resilience | MyPNG / Core | **IMPLEMENTED** | `frappe.email.doctype.email_account.email_account.pull`. Logs errors and resumes pulling unread/unseen messages by UID upon reconnect. |
| **15** | **System Backup & Recovery Drill** (`OPS-02`)| Operations | MyPNG / Bench | **IMPLEMENTED** *(CLI)* | Backups supported via `bench backup --with-files` and Docker named volume persistence (`mariadb-data`, `bench-data`). |
| **16** | **Problem / Incident Ticket Hierarchy** | Ticket Lifecycle | Zendesk | **IMPLEMENTED** | `hd_ticket.json` (`problem_ticket`, `incident_count`), `hd_ticket.py`, `helpdesk/api/problem_incident.py`. Allows linking child incidents to parent problem with counter tracking and mass resolution propagation. |
| **17** | **Guest / Anonymous Ticket Submission** | Ticket Intake | Zendesk | **IMPLEMENTED** | `helpdesk/api/guest_ticket.py`, `hd_ticket.json` (`guest_token`, `is_guest_ticket`). Tokenized 32-byte cryptographic magic-link portal access without mandatory user registration. |
| **18** | **Omnichannel Intake (Widget / Webhooks)** | Ticket Intake | Zendesk | **IMPLEMENTED** | `helpdesk/api/widget.py`, `helpdesk/public/js/helpdesk-widget.js`. Drop-in embeddable JS widget for external websites with live KB search and guest ticket intake. |
| **19** | **Event-Driven Trigger Engine** | Automation | Zendesk | **IMPLEMENTED** | `helpdesk/doctype/hd_trigger/`, `helpdesk/automation/trigger_engine.py`, `hd_ticket.py`. Evaluates event triggers (`On Ticket Creation`, `On Ticket Update`, `On Status Change`) and executes actions (`Set Status`, `Set Priority`, `Set Team`, `Add Tag`, `Remove Tag`). |
| **20** | **Time-Driven Automations & Escalations** | Automation | Zendesk | **IMPLEMENTED** | `helpdesk/doctype/hd_automation/`, `helpdesk/automation/automation_engine.py`, `hooks.py`. Evaluates elapsed time conditions on hourly scheduler and executes progressive actions. |
| **21** | **Dynamic Macro Templating in Replies** | Productivity | Zendesk | **IMPLEMENTED** | `helpdesk/api/saved_replies.py`. Jinja template rendering of `ticket`, `customer`, `contact`, `agent`, and `current_user` in canned responses. |
| **22** | **Side Conversations** | Collaboration | Zendesk | **IMPLEMENTED** | `helpdesk/doctype/hd_side_conversation/`, `hd_side_conversation_message/`, `helpdesk/api/side_conversation.py`. Sub-threads for third-party vendors shielded completely from customer portal. |
| **23** | **Agent Collision / Takeover Locking** | Collaboration | Zendesk | **IMPLEMENTED** | `helpdesk/api/agent_lock.py`. Distributed TTL locking in Redis cache with collision detection, realtime events, force takeover, and email signature injection in `reply_via_agent()`. |
| **24** | **Skill-Based Ticket Assignment** | Routing | Zendesk | **IMPLEMENTED** | `HD Skill`, `HD Agent Skill`, `HD Ticket Skill`, `helpdesk/overrides/assignment_rule.py`. Matches ticket skill requirements with qualified agents. |
| **25** | **Agent Workload Capacity Limits** | Routing | Zendesk | **IMPLEMENTED** | `HD Agent.max_concurrent_tickets`, `helpdesk/overrides/assignment_rule.py`. Workload capacity enforcement with least-loaded fallback. |
| **26** | **VIP / Priority CGD Routing Rules** | Routing | MyPNG / Zendesk | **IMPLEMENTED** | `helpdesk/doctype/hd_vip_routing_rule/`, `hd_customer.json`, `hd_ticket.py` (`apply_vip_routing`, `apply_vip_tag`), `helpdesk/overrides/assignment_rule.py`, `VipRoutingConfig.vue`. Automatic priority escalation, dedicated VIP team routing, fast-track SLA policies, `#vip-cgd` badges, and senior agent assignment for key CGD accounts (e.g. GAIL, BPCL). |
| **27** | **Configurable State Transition Guards** | State Management | Zendesk | **IMPLEMENTED** | `helpdesk/doctype/hd_status_transition_guard/`, `hd_ticket.py` (`validate_status_transition`). Enforces strict `from_status` $\rightarrow$ `to_status` state workflows and restricts transitions by role. |
| **28** | **Conditional Mandatory Fields on Status** | State Management | Zendesk | **IMPLEMENTED** | `helpdesk/doctype/hd_status_transition_guard/`, `hd_ticket.py`. Enforces required fields (e.g., `resolution_details`) before transitioning to target statuses. |
| **29** | **Live SLA Countdown Badges** | Reporting / SLA | Zendesk | **IMPLEMENTED** | `helpdesk/api/sla_metrics.py`. Dynamic real-time SLA countdown badges (`healthy`, `urgent`, `breached`, `fulfilled`) and human duration calculations. |
| **30** | **CSAT & NPS Survey Engine** | Feedback / QA | Zendesk | **IMPLEMENTED** | `helpdesk/doctype/hd_csat_survey/`, `helpdesk/api/csat.py`. Automated survey email triggers upon ticket resolution, 1-5 one-click rating links, feedback synchronization, and agent scorecard leaderboards. |
| **31** | **Custom Ad-Hoc Report Builder & Multi-Format Exports** | Reporting / Analytics | Zendesk | **IMPLEMENTED** | `helpdesk/api/custom_reports.py`, `CgdDistributionCard.vue`, `CustomReportsModal.vue`. Multi-dimensional analytics grouped by customer, team, priority, status; multi-format exports (CSV, JSON, print-ready HTML/PDF); on-demand email digests; CGD entity distribution card; and 24h hourly ticket heatmaps. |
| **32** | **Granular Roles (Tier 1, Tier 2, Lead, Auditor)** | RBAC | MyPNG / Zendesk | **IMPLEMENTED** | `HD Tier 1 Agent`, `HD Tier 2 Agent`, `HD Team Lead`, `HD Auditor` in `setup/install.py`, `hd_ticket.py` (`validate_granular_role_permissions`, `validate_trash_permissions`, `has_permission`). |
| **33** | **Outgoing Webhooks Engine (Slack/Teams)** | Extensibility | Zendesk | **IMPLEMENTED** | `helpdesk/doctype/hd_webhook/`, `hd_webhook_log/`, `helpdesk/automation/webhook_engine.py`. Event-driven webhook delivery with HMAC SHA-256 signatures, customer filters, custom headers, and audit logs. |
| **34** | **Customer Portal Enhancement & Multi-CGD Branding** | Portal / Branding | MyPNG / Zendesk | **IMPLEMENTED** | `helpdesk/api/portal.py`, `test_portal_branding.py`, `CgdPortalBanner.vue`, `portal.ts`, `TicketCustomerSidebar.vue`. Dynamic entity logos & banners per CGD entity (BPCL, GAIL, IGL), VIP priority status tags, live SLA countdown badges on customer portal, and 1-5 star CSAT rating widget. |



---

## 3. Deep-Dive: Multi-Tenant CGD Isolation & Inbound Email (MyPNG Requirements)

### 3.1. Inbound Processing & Duplicate Deduplication (`MAIL-01`, `MAIL-02`, `MAIL-03`)
- **Implemented Logic**:
  - `helpdesk/overrides/email_account.py` provides `CustomEmailAccount` and `CustomInboundMail`.
  - When an incoming email arrives, `CustomInboundMail.parent_communication()` checks `In-Reply-To` and walks back through all message IDs in the `References` header. If a previous message is found on an `HD Ticket`, the incoming communication is attached to that ticket.
  - **Duplicate Message Handling (`MAIL-03`)**: Frappe core's `InboundMail.process()` executes:
    ```python
    communication = self.is_exist_in_system()
    if communication:
        communication.update_db(uid=self.uid)
        return communication
    ```
    This prevents duplicate deliveries of the same email from spawning multiple tickets.

### 3.2. Automated Domain-Based Customer Mapping (`MAIL-01`, `MAIL-04`)
- **Implemented Architecture**:
  - **DocType `HD Domain Mapping`**:
    - Fields: `domain` (Data, unique, auto-cleaned via `clean_domain` in `autoname` and `validate`), `customer` (Link to `HD Customer`), `default_team` (Link to `HD Team`), `is_active` (Check), `description` (Small Text).
    - Lifecycle hooks: `autoname` sets `self.name = self.domain` after stripping `@` and converting to lowercase.
  - **Ticket Routing & Linking (`hd_ticket.py`)**:
    - `map_customer_from_domain()` checks `HD Domain Mapping` by sender email domain, falling back to `HD Customer.domain`.
    - If mapped, automatically creates/links `Contact` to the customer organization and sets `self.customer` and `self.agent_group`.
    - `handle_unclassified_ticket()` & `apply_unclassified_tag()`: If unmapped, assigns `HD Settings.unclassified_team` and attaches the `unclassified-cgd` tag for agent triage.
  - **Desk Settings Management**:
    - Managed via `DomainMappingsConfig.vue` integrated into the `SettingsModal` under `App Settings`.
  - **Verification**: Fully validated by unit tests in `helpdesk/tests/test_domain_mapping.py` (4/4 tests passed).

### 3.3. Outbound Sender Identity & Email Branding (`MAIL-05`)
- **Implemented Logic**:
  - In `hd_ticket.py:reply_via_agent()`, the system looks up the default outgoing email account via `helpdesk/helpdesk/utils/email.py`.
- **Configuration Requirement**:
  - Set the outgoing `Email Account` name to `My Support PNG` and sender address to `support@mypng.test` (or M365 production address).

### 3.4. Multi-Tenant Security & Strict CGD Isolation (`SEC-01`, `SEC-02`, `SEC-03`)
- **Implemented Logic**:
  - **SEC-01 (URL Access)**: `hd_ticket.py:has_permission()` validates access:
    ```python
    if user in (doc.contact, doc.raised_by, doc.owner): return True
    if _is_customer_manager(doc.customer, user): return True
    if not is_agent(user): return False
    ```
  - **SEC-02 (Search Isolation)**: `helpdesk/search_sqlite.py` filters results against `_get_accessible_tickets()`, which invokes `frappe.get_list('HD Ticket')`, strictly enforcing `permission_query`.
  - **SEC-03 (Attachment Access)**: Files inherit parent document permissions.

### 3.5. Portal Account Approval & Onboarding Workflow (`SEC-04`)
- **Implemented Architecture**:
  - **DocType `HD Customer Signup Request`**:
    - Fields: `email`, `full_name`, `phone`, `requested_cgd`, `designation`, `status` (`Pending`, `Approved`, `Rejected`), `assigned_role`, `rejection_reason`, `reviewed_by`, `reviewed_on`.
    - Methods:
      - `approve(customer, role)`: Provisions/enables `User` as `Website User`, provisions `Contact`, links contact into `HD Customer.contacts`, assigns `HD Customer` or `HD Customer Manager` role, and marks request `Approved`.
      - `reject(reason)`: Records rejection reason and auditor timestamps without creating user accounts.
  - **Whitelisted Endpoints (`helpdesk/api/customer_signup.py`)**:
    - `submit_signup_request`: Public submission (accessible by Guest) with deduplication against pending requests and active users.
    - `get_pending_signup_requests`, `approve_signup_request`, `reject_signup_request`: Restricted to `Agent Manager` or `System Manager`.
  - **Desk Approval Queue UI**:
    - Managed via `SignupRequestsConfig.vue` integrated into `SettingsModal` under `App Settings`.
  - **Verification**: Fully validated by unit tests in `helpdesk/tests/test_customer_signup.py` (5/5 tests passed).

### 3.6. Internal Notes Shielding (`SEC-05`)
- **Implemented Logic**:
  - `helpdesk/extends/comment.py` overrides `Comment` permissions:
    ```python
    def can_see_ticket_comments(ticket: str, user: str | None = None) -> bool:
        if is_admin(user): return True
        if not is_agent(user): return False
        return bool(frappe.has_permission("HD Ticket", "read", doc=ticket, user=user))
    ```
  - Ensures customers can never view internal comments, reactions, or agent-only files.

---

## 4. Zendesk-Grade Helpdesk Enhancements (Specifications)

### 4.1. Advanced Ticket Relations (Problem & Incident Hierarchy)

```
                       ┌──────────────────────────────────┐
                       │   Master Problem Ticket (P-101)  │
                       │   "GAIL ERP API Gateway Down"    │
                       └────────────────┬─────────────────┘
                                        │
           ┌────────────────────────────┼────────────────────────────┐
           ▼                            ▼                            ▼
┌───────────────────────┐    ┌───────────────────────┐    ┌───────────────────────┐
│ Child Incident #102   │    │ Child Incident #103   │    │ Child Incident #104   │
│ Customer: GAIL North  │    │ Customer: GAIL South  │    │ Customer: GAIL Delhi  │
└───────────────────────┘    └───────────────────────┘    └───────────────────────┘
```

- **Implementation Architecture & Details (`IMPLEMENTED & TESTED`)**:
  - **Schema Updates (`hd_ticket.json`)**: Added `problem_ticket` (Link to `HD Ticket`) and `incident_count` (Int, read-only counter). Added `"Problem"` and `"Task"` to standard ticket types in `helpdesk/setup/ticket_type.py`.
  - **Counter Synchronization (`hd_ticket.py`)**: `sync_problem_incident_count()` automatically tracks child incidents on insert, link update, and trash, maintaining exact incident counters on master problem tickets.
  - **Mass Resolution Propagation (`hd_ticket.py`)**: `handle_problem_status_change()` and `propagate_resolution_to_incidents()` detect problem ticket resolution, automatically updating all open linked incidents with resolution details, status, and audit comments.
  - **Whitelisted Endpoints (`helpdesk/api/problem_incident.py`)**: Exposes `get_linked_incidents`, `link_incident_to_problem`, `unlink_incident_from_problem`, and `propagate_problem_resolution`.
  - **Verification**: Fully validated by unit tests in `helpdesk/tests/test_problem_incident.py` (2/2 tests passed).

---

### 4.2. Visual Automation Engine: Triggers & Time-Driven Automations

Frappe Helpdesk has explicit code comments acknowledging the need for a rule engine (`# TODO: remove this feature once we add automation feature`).

```
[Event-Driven: Triggers]
Ticket Insert / Update / Reply
       │
       ▼
Evaluate Conditions (ALL: AND / ANY: OR)
       │
       ▼
Execute Immediate Actions (Set Field, Reassign, Notify, Add Tag, Webhook)

[Time-Driven: Automations (Cron)]
Scheduled Job (Hourly / 15-min)
       │
       ▼
Match Tickets Inactive for X Hours / SLA Breach Risk
       │
       ▼
Execute Progressive Actions (Send Reminder, Escalate Priority, Auto-Solve)
```

- **Implementation Architecture & Details (`IMPLEMENTED & TESTED`)**:
  1. **DocType `HD Trigger` & Execution Engine (`trigger_engine.py`)**:
     - **Event Triggers**: `On Ticket Creation`, `On Ticket Update`, `On Status Change`.
     - **Condition Operators**: `==`, `!=`, `contains`, `in`, `is_set`, `changed_to` evaluated via `All` (AND) or `Any` (OR) logic.
     - **Action Suite**: `Set Status`, `Set Priority`, `Set Team`, `Add Tag`, `Remove Tag`.
     - **Save Discipline & Recursion Protection**: Integrated directly into `hd_ticket.py` lifecycle hooks (`before_insert`, `before_save`, `after_insert`) with `ticket.flags.in_trigger_execution` recursion guards. Field mutations occur in-memory without extra database writes.
     - **Verification**: Fully validated by unit tests in `helpdesk/tests/test_triggers.py` (2/2 tests passed).
  2. **DocType `HD Automation` & Scheduled Engine (`automation_engine.py`)**:
     - **Time Criteria**: Evaluates `hours_since_last_customer_response`, `hours_since_last_agent_response`, and `hours_since_created` against document timestamps.
     - **Scheduler**: Hourly execution registered in `helpdesk/hooks.py` (`helpdesk.automation.automation_engine.execute_automations`).
     - **Action Suite**: Executes progressive status updates, priority escalations, team reassignment, and tagging.
     - **Verification**: Fully validated by unit tests in `helpdesk/tests/test_automations.py` (1/1 test passed).
  3. **Dynamic Macro Templating in Saved Replies (`saved_replies.py`)**:
     - **Jinja Macro Expansion**: `get_saved_reply_context(ticket)` and `get_rendered_saved_reply()` interpolate rich variables including `{{ ticket.name }}`, `{{ customer.customer_name }}`, `{{ contact.email }}`, `{{ agent.agent_name }}`, `{{ current_user.full_name }}`, and `{{ now }}`.
     - **Verification**: Fully validated by unit tests in `helpdesk/tests/test_macro_templating.py` (1/1 test passed).

---

### 4.3. Skill-Based Routing & Agent Capacity Limits

- **Implementation Architecture & Details (`IMPLEMENTED & TESTED`)**:
  1. **DocTypes `HD Skill`, `HD Agent Skill`, and `HD Ticket Skill`**:
     - `HD Skill`: Master technical and domain skills catalog (e.g., `SCADA Integration`, `Billing & Invoicing`, `Pipeline Infrastructure`).
     - `HD Agent Skill`: Child table linking skills to agents (`HD Agent.skills`).
     - `HD Ticket Skill`: Child table linking required technical skills to tickets (`HD Ticket.skills`).
  2. **Agent Workload Capacity & Smart Assignment Rule (`assignment_rule.py`)**:
     - Added `max_concurrent_tickets` (Int, default 10) on `HD Agent`.
     - `HelpdeskAssignmentRule.get_user()` in `helpdesk/overrides/assignment_rule.py` extended with multi-tier filtering:
       - **Skill Match Filter**: Matches `ticket.skills` against agents possessing required skills (`get_agents_with_skills()`).
       - **Capacity Limit Filter**: Filters agents who are under their `max_concurrent_tickets` limit (`is_agent_under_capacity()`). If all matching agents are saturated, dynamically falls back to the least-loaded qualified agent.
       - **Availability Tiers**: Prioritizes `Active` agents over `Away` or `Unavailable`.
     - **Verification**: Fully validated by unit tests in `helpdesk/tests/test_skill_routing.py` (2/2 tests passed).

---


### 4.4. State Machine Guards & Conditional Mandatory Fields

- **Problem Statement**: Agents can transition a ticket between any status without validation, and tickets can be marked `Resolved` without documenting root causes.
- **Implementation Architecture & Details (`IMPLEMENTED & TESTED`)**:
  1. **DocType `HD Status Transition Guard`**:
     - Fields: `from_status` (Link to `HD Ticket Status`), `to_status` (Link to `HD Ticket Status`), `allowed_roles` (Comma-separated roles), `required_fields` (Comma-separated fieldnames, e.g., `resolution_details`), `error_message` (Custom ValidationError text), `is_active` (Check).
     - Enforces state machine flows (e.g., preventing jumping from `Open` to `Closed` without passing through `Resolved`).
  2. **Role & Conditional Mandatory Field Validation (`hd_ticket.py`)**:
     - Hooked into `validate_status_transition()` during ticket `validate()` lifecycle hook.
     - Verifies user has at least one of the `allowed_roles` (or System Manager).
     - Verifies all `required_fields` are non-empty before permitting status change.
     - **Verification**: Fully validated by unit tests in `helpdesk/tests/test_status_guards.py` (2/2 tests passed).

---

### 4.5. Collaboration: Side Conversations & Agent Collision Locking

- **Implementation Architecture & Details (`IMPLEMENTED & TESTED`)**:
  1. **Side Conversations (`HD Side Conversation` & `HD Side Conversation Message`)**:
     - Supports independent email recipients (vendors, external consultants) with independent subject/body and conversation status (`Open`, `Closed`).
     - Strictly protected by `has_permission` hooks (`hd_side_conversation.py`, `hd_side_conversation_message.py`) so customer portal users have zero read or write access.
     - Whitelisted API endpoints in `helpdesk/api/side_conversation.py`: `create_side_conversation`, `get_side_conversations`, `reply_to_side_conversation`, `close_side_conversation`, `reopen_side_conversation`.
     - Fully validated by unit tests in `helpdesk/tests/test_side_conversation.py` (2/2 tests passed).
  2. **Active Edit Lock & Takeover Protection (`agent_lock.py`)**:
     - Built distributed Redis cache lock with TTL (`LOCK_TTL_SECONDS = 120`).
     - Emits real-time Socket.IO events (`helpdesk:ticket_locked`, `helpdesk:ticket_unlocked`, `helpdesk:ticket_lock_taken_over`).
     - Whitelisted API endpoints in `helpdesk/api/agent_lock.py`: `acquire_ticket_lock`, `get_ticket_lock`, `release_ticket_lock`.
     - Supports collision detection and explicit `force=True` takeover by other agents.
     - Fully validated by unit tests in `helpdesk/tests/test_agent_lock.py` (2/2 tests passed).
  3. **Customizable Email Signatures & Reply Propagation**:
     - Added `signature` (Small Text) field on `HD Agent`.
     - Automatically appends agent's signature in `HDTicket.reply_via_agent()`.
     - Supports `propagate_to_incidents=True` in `reply_via_agent()` to mirror replies to child incidents.
     - Fully validated by unit tests in `helpdesk/tests/test_agent_signature.py` (2/2 tests passed).

---

### 4.6. Reporting, CSAT & Analytics

- **Implementation Architecture & Details**:
  1. **Visual SLA Countdown Badges & Metrics API (`sla_metrics.py`) (`IMPLEMENTED & TESTED`)**:
     - Endpoint `helpdesk.api.sla_metrics.get_ticket_sla_metrics` provides real-time SLA metrics for both Response and Resolution SLA dimensions:
       - **Badge Statuses**: `healthy` (> 30 mins left), `urgent` (< 30 mins left), `breached` (past target), and `fulfilled` (responded / resolved).
       - **Human Duration**: Shorthand countdowns (e.g., `45m left`, `2h 15m left`, `Breached by 1h 20m`, `Responded`, `Resolved`).
     - **Verification**: Fully validated by unit tests in `helpdesk/tests/test_sla_countdown.py` (1/1 test passed).
  2. **Automated CSAT / NPS Engine (`TO BE DEVELOPED IN PHASE 5`)**:
     - Upon ticket status moving to `Resolved`, automatically trigger a survey email with 1-5 rating buttons.
     - Customer response records into `HD CSAT Response` DocType.
  3. **Custom Report Builder (`TO BE DEVELOPED IN PHASE 5`)**:
     - UI component allowing managers to generate custom tabular and chart reports with export to Excel/PDF.

---

### 4.7. Role-Based Access Control (RBAC) & Guest Intake

- **Implementation Architecture & Details (`IMPLEMENTED & TESTED`)**:
  1. **Granular Agent Tiers & Auditor Role (`hd_ticket.py`, `setup/install.py`)**:
     - Provisioned standard roles via `setup_granular_agent_roles()`: `HD Tier 1 Agent`, `HD Tier 2 Agent`, `HD Team Lead`, `HD Auditor`.
     - **HD Tier 1 Agent**: Permitted to reply and manage active tickets, but strictly blocked in `validate_granular_role_permissions()` and `validate_trash_permissions()` from merging tickets (`is_merged`), mutating SLA policies (`sla`), or deleting tickets.
     - **HD Auditor**: Granted global read access via `has_permission()` and DocPerm, but strictly blocked from modifying ticket data or deleting tickets.
     - **HD Team Lead & HD Tier 2 Agent**: Advanced permissions for routing modifications and full ticket lifecycle control.
     - **Verification**: Fully validated by unit tests in `helpdesk/tests/test_granular_roles.py` (2/2 tests passed).
  2. **Guest Ticket Intake & Cryptographic Magic-Link Access (`guest_ticket.py`)**:
     - Endpoint `helpdesk.api.guest_ticket.submit_guest_ticket` (`allow_guest=True`): Allows public ticket submission without requiring user registration. Auto-links/creates contact and generates a 32-byte URL-safe cryptographic token (`guest_token`).
     - Endpoint `get_guest_ticket_details`: Validates magic-link token to return sanitized public ticket status and communication timeline (shielding internal comments and side conversations).
     - Endpoint `guest_reply_to_ticket`: Validates magic-link token and allows requesters to post replies into ticket communications thread.
     - **Verification**: Fully validated by unit tests in `helpdesk/tests/test_guest_magic_link.py` (3/3 tests passed).
  3. **Multi-Brand Portal Support (`TO BE DEVELOPED`)**:
     - Distinct portal themes, domains, and email headers per brand.

---


## 5. Technical Data Model Blueprint (New DocTypes Required)

The following DocTypes and schemas are specified for future implementation:

```
┌─────────────────────────┐          ┌─────────────────────────┐
│    HD Domain Mapping    │          │   HD Automation Rule    │
├─────────────────────────┤          ├─────────────────────────┤
│ domain (Data, Unique)   │          │ rule_name (Data)        │
│ customer (Link Customer)│          │ trigger_type (Select)   │
│ default_team (Link Team)│          │ conditions_json (Code)  │
│ is_active (Check)       │          │ actions_json (Code)     │
└─────────────────────────┘          │ is_enabled (Check)      │
                                     └─────────────────────────┘
┌─────────────────────────┐          ┌─────────────────────────┐
│       HD Skill          │          │  HD Side Conversation   │
├─────────────────────────┤          ├─────────────────────────┤
│ skill_name (Data)       │          │ parent_ticket (Link)    │
│ category (Select)       │          │ recipients (Data)       │
│ description (Small Text)│          │ subject (Data)          │
└─────────────────────────┘          │ messages (Long Text)    │
                                     └─────────────────────────┘
┌─────────────────────────┐          ┌─────────────────────────┐
│     HD CSAT Survey      │          │  HD Status Transition   │
├─────────────────────────┤          ├─────────────────────────┤
│ ticket (Link HD Ticket) │          │ from_status (Link)      │
│ rating (Int: 1 to 5)    │          │ to_status (Link)        │
│ feedback (Small Text)   │          │ required_fields (Data)  │
│ submitted_by (Data)     │          │ allowed_roles (Data)    │
└─────────────────────────┘          └─────────────────────────┘
```

---

## 6. Phased Implementation Roadmap

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: MyPNG Compliance & Multi-Tenant Routing [COMPLETED & TESTED]                       │
│ • [x] Implement HD Domain Mapping for automatic CGD assignment (e.g. @bpcl.in -> BPCL)      │
│ • [x] Establish default "Unclassified" queue routing for unmapped domains                   │
│ • [x] Verify outbound identity branding ("My Support PNG" / support@mypng.test)             │
│ • [x] Build Admin Approval Queue UI for portal self-registrations                           │
└──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                               │
┌──────────────────────────────────────────────▼──────────────────────────────────────────────┐
│ PHASE 2: Workflow Automation & State Transition Controls [COMPLETED & TESTED]                │
│ • [x] Build Event-Driven Trigger Engine (HD Trigger)                                         │
│ • [x] Build Time-Driven Automation Engine (HD Automation) for multi-stage escalations        │
│ • [x] Implement Status Transition Guards and mandatory fields on resolution                  │
│ • [x] Add Dynamic Macro Templating with liquid/jinja placeholders for saved replies          │
└──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                               │
┌──────────────────────────────────────────────▼──────────────────────────────────────────────┐
│ PHASE 3: Agent Collaboration & Advanced Ticket Relations [COMPLETED & TESTED]                │
│ • [x] Implement Problem/Incident hierarchy with mass resolution propagation                  │
│ • [x] Implement Side Conversations for third-party and vendor discussions                    │
│ • [x] Implement Active Edit Locking to prevent reply collision and overwrites                │
│ • [x] Introduce customizable email signatures per agent and per mailbox                      │
└──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                               │
┌──────────────────────────────────────────────▼──────────────────────────────────────────────┐
│ PHASE 4: Capacity Routing, SLA & Granular RBAC [COMPLETED & TESTED]                          │
│ • [x] Implement Skill-Based Routing and Agent Workload Capacity Caps                         │
│ • [x] Configure Granular Roles (Tier 1, Tier 2, Team Lead, Auditor)                         │
│ • [x] Render visual SLA breach countdown timers in ticket views                             │
│ • [x] Introduce guest/magic-link ticket tracking without mandatory account creation          │
└──────────────────────────────────────────────┬──────────────────────────────────────────────┘

                                               │
┌──────────────────────────────────────────────▼──────────────────────────────────────────────┐
│ PHASE 5: Omnichannel Intake, CSAT, Multi-CGD Portal Branding [COMPLETED & TESTED]           │
│ • [x] Deliver Embeddable JavaScript Customer Chat / Support Widget                          │
│ • [x] Build automated CSAT / NPS Survey Engine with agent leaderboards                      │
│ • [x] Develop Outgoing Webhook Engine with HMAC SHA-256 signatures                           │
│ • [x] Implement Custom Report Builder and scheduled PDF/CSV digest exports                  │
│ • [x] Customer Portal Enhancement & Multi-CGD Branding (dynamic logo, banner, portal CSAT)  │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Operational Reference & Verification Checklist

When implementing enhancements, verify compliance against the test suite defined in `PROJECT_OVERVIEW.md`:

- [x] **MAIL-01**: Inbound email creates a tracked ticket with proper mapping.
- [x] **MAIL-02**: Inbound reply stitches onto existing ticket thread.
- [x] **MAIL-03**: Duplicate email delivery with identical `Message-ID` does not create duplicate tickets.
- [x] **MAIL-04**: Unknown sender/domain routes to triage without false mapping.
- [x] **MAIL-05**: Agent reply originates from authorized system identity.
- [x] **SEC-01**: Direct URL manipulation across CGD boundaries is denied.
- [x] **SEC-02**: Ticket search is restricted to the user's CGD organization.
- [x] **SEC-03**: Attachment downloads across CGD boundaries are denied.
- [x] **SEC-04**: Self-registered portal accounts require explicit admin approval before activation.
- [x] **SEC-05**: Internal agent comments are completely hidden from customer portals and notifications.
- [x] **OPS-01**: Mailbox outage recovers and reconciles message backlog upon reconnection.
- [x] **OPS-02**: Backup and restore procedures maintain exact ticket and attachment integrity.

# PNG Support Portal (MyPNG Support Desk)

[![Frappe Framework](https://img.shields.io/badge/Frappe%20Framework-v15-blue.svg)](https://frappeframework.com/)
[![Vue 3](https://img.shields.io/badge/Frontend-Vue%203%20%2B%20TypeScript-42b883.svg)](https://vuejs.org/)
[![Vite](https://img.shields.io/badge/Bundler-Vite-646CFF.svg)](https://vitejs.dev/)
[![Docker](https://img.shields.io/badge/Container-Docker%20Compose-2496ED.svg)](https://www.docker.com/)

**PNG Support Portal** is an enterprise-grade customer support and helpdesk platform built on [Frappe Framework](https://github.com/frappe/frappe) (Python / MariaDB / Redis) and [Frappe UI](https://github.com/frappe/frappe-ui) (Vue 3 / TypeScript SPA).

The platform consolidates Zendesk-class ticketing workflows with dedicated multi-tenant capabilities designed for **City Gas Distribution (CGD) entities** (e.g., BPCL, GAIL, IGL). It allows multiple organizations to share centralized agent operations while strictly isolating customer data, inquiries, and portal access.

---

## Table of Contents

- [Key Features](#key-features)
- [Architecture & Tech Stack](#architecture--tech-stack)
- [Prerequisites](#prerequisites)
- [Getting Started (Docker - Recommended)](#getting-started-docker---recommended)
  - [1. Start Docker Daemon](#1-start-docker-daemon)
  - [2. Launch the Application](#2-launch-the-application)
  - [3. Access the Application & Default Credentials](#3-access-the-application--default-credentials)
- [Frontend Development & Build](#frontend-development--build)
- [Native Bench Setup (Alternative)](#native-bench-setup-alternative)
- [Common Operations & Bench Commands](#common-operations--bench-commands)
- [Project Structure](#project-structure)
- [Support Mailbox Integration (Microsoft 365)](#support-mailbox-integration-microsoft-365)
- [Role-Based Access Control (RBAC) Architecture](#role-based-access-control-rbac-architecture)
  - [1. Admin Role vs. User Role](#1-admin-role-vs-user-role)
  - [2. Module Access Matrix](#2-module-access-matrix)
  - [3. Dedicated Login Flow & Post-Login Redirection](#3-dedicated-login-flow--post-login-redirection)
  - [4. Direct URL Protection (Frontend Guard)](#4-direct-url-protection-frontend-guard)
  - [5. Backend API Enforcement & DocType Filtering](#5-backend-api-enforcement--doctype-filtering)
  - [6. Provisioning & Testing RBAC](#6-provisioning--testing-rbac)
- [Troubleshooting & FAQs](#troubleshooting--faqs)

---

## Key Features

### 1. Multi-Tenant CGD Security & Isolation
- **Strict Data Segregation**: Automatic tenant enforcement preventing cross-CGD access to tickets, attachments, search results, or comments.
- **Dynamic Multi-CGD Branding**: Custom banners, logos, and portal headers dynamically rendered according to the logged-in customer entity (e.g., BPCL, GAIL, IGL).
- **Domain-Based Auto Customer Mapping**: Inbound emails and user registrations are mapped automatically to their respective CGD entity based on sender domain.
- **Internal Notes Shielding**: Proprietary internal discussion threads are strictly invisible to customer portal users.

### 2. Intelligent Inbound Email Processing
- **Email Ingestion to Ticket**: Seamless conversion of incoming emails into tickets and communications.
- **Thread Stitching**: Robust conversation tracking via `In-Reply-To` and `References` headers.
- **Message-ID Deduplication**: Automatic deduplication preventing duplicate tickets from multi-recipient or bounced emails.
- **Unknown Sender Triage**: Unmatched inbound inquiries route to an unclassified queue with automated tagging.

### 3. Zendesk-Grade Automation & Routing
- **Event-Driven Triggers**: Configurable rule engine triggering automated field changes, priority assignments, team routing, and tag adjustments on creation/update.
- **Time-Driven Automations**: Scheduled background jobs for auto-closing stale tickets, escalation warnings, and SLA alerts.
- **Skill-Based & Capacity Routing**: Dispatches tickets to agents possessing required skill proficiencies while respecting concurrent ticket limits.
- **VIP Routing Rules**: Fast-track priority assignment and dedicated support teams for strategic CGD accounts.

### 4. Agent Productivity & Collaboration
- **Agent Collision Locking**: Distributed Redis-backed lock management warning agents when another team member is actively viewing or editing a ticket, with collision takeover capabilities.
- **Side Conversations**: Isolated sub-threads for communication with external third-party vendors without exposing discussions to the customer.
- **Problem / Incident Management**: Link related incident tickets to a parent problem ticket for collective updates and mass resolution.
- **Canned Responses & Dynamic Macros**: Jinja-powered templating for ticket, customer, and agent details in saved replies.

### 5. Omnichannel Ticket Intake
- **Embeddable Helpdesk Widget**: Drop-in JavaScript widget providing self-service knowledge base search and ticket creation.
- **Guest / Anonymous Intake**: Cryptographic magic links allow guest ticket creation and tracking without mandatory pre-registration.
- **Customer Self-Service Portal**: Ticket history, real-time SLA countdown badges, status trackers, and knowledge base.

### 6. SLA Tracking & CSAT Analytics
- **Live SLA Countdown Badges**: Dynamic visual indicators (`healthy`, `urgent`, `breached`, `fulfilled`) based on business hours and holiday lists.
- **Automated CSAT / NPS Surveys**: Triggered upon ticket resolution with 1-click rating links and agent scorecards.
- **Ad-Hoc Custom Reports & Exports**: Multi-dimensional analytics exportable to CSV, JSON, and print-ready HTML/PDF.

---

## Architecture & Tech Stack

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

- **Backend**: Python 3.10–3.14, [Frappe Framework](https://frappeframework.com/) (Version 15)
- **Database**: MariaDB 10.8+
- **In-Memory Cache & Pub/Sub**: Redis (Cache, Worker Queue, Socket.IO)
- **Frontend**: Vue 3, TypeScript, Vite, Tailwind CSS, Pinia, [Frappe UI](https://github.com/frappe/frappe-ui), Lucide Icons
- **Realtime**: Socket.IO Node.js server
- **Containerization**: Docker Compose (`frappe/bench:latest`, `mariadb:10.8`, `redis:alpine`)

---

## Prerequisites

Before running the project, ensure your workstation has:

1. **Docker & Docker Compose**:
   - **Windows**: [Docker Desktop](https://www.docker.com/products/docker-desktop/) with WSL 2 backend enabled.
   - **macOS / Linux**: Docker Engine 24.0+ and Docker Compose v2.
2. **Git**: Installed and configured on your system.
3. *(Optional - for host frontend development)*:
   - **Node.js**: v18.x, v20.x, or v24.x
   - **Yarn**: v1.22+ (enable using `corepack enable` if on Node 18+)

---

## Getting Started (Docker - Recommended)

The repository provides a complete containerized environment in `docker/` that provisions MariaDB, Redis, Frappe Bench, Telephony, and Helpdesk with zero manual database configuration.

### 1. Start Docker Daemon
Make sure Docker Desktop or the Docker service is actively running on your host machine:

```powershell
# Verify Docker is responding
docker ps
```

### 2. Launch the Application
Navigate to the `docker/` directory and spin up the containers:

```powershell
cd docker
docker compose up -d
```

#### What happens automatically on first boot:
- MariaDB (`docker-mariadb-1`) and Redis (`docker-redis-1`) initialize.
- The Frappe container executes [docker/init.sh](file:///C:/Users/rajat.agashe/Desktop/PNG_Project/PNG_Support_Portal/docker/init.sh):
  - Initializes a new bench (`version-15`) if not already present.
  - Connects to containerized MariaDB and Redis services.
  - Installs the `telephony` and `helpdesk` apps.
  - Creates the site `helpdesk.localhost` with developer mode enabled.
  - Starts the backend server, background worker, scheduler, and Socket.IO real-time server via `bench start`.

*(Note: On initial creation, fetching dependencies and provisioning the site takes a few minutes. Subsequent launches start in seconds).*

### 3. Access the Application & Default Credentials

Once the containers are up, the portal is ready to use:

| Interface | URL | Description |
| :--- | :--- | :--- |
| **PNG Support Desk (Portal)** | [http://localhost:8000/helpdesk](http://localhost:8000/helpdesk) | Main SPA (auto-redirects based on logged-in role) |
| **Dedicated Portal Login** | [http://localhost:8000/helpdesk/login](http://localhost:8000/helpdesk/login) | Role-aware login with one-click credential switcher |
| **Frappe Desk / Admin Login** | [http://localhost:8000/login](http://localhost:8000/login) | Standard Frappe administrative interface |
| **Realtime Service** | `ws://localhost:9000` | Live ticket updates, typing presence, collision locks |

#### Role Access & Environment Secrets

Credentials are securely managed through environment variables (`.env`) and must never be committed to Git. See `.env.example` to set local secrets.

| Role | Username / Identity | Credential Source | Access Scope |
| :--- | :--- | :--- | :--- |
| **Admin** | `Administrator` | `ADMIN_PASSWORD` in `.env` | **Full Access** to all modules, settings, reports, agents, and configuration. |
| **User** | `support.png@amantyatech.com` | `SUPPORT_USER_PASSWORD` in `.env` | **Support Email Management ONLY** (`/support-emails`). All other modules are strictly blocked. |
| *(Legacy)* | `user@example.com` | `SUPPORT_USER_PASSWORD` in `.env` | Secondary support email operator account. |

---

## Frontend Development & Build

The frontend is located under `desk/` and is built as a single-page application using Vue 3 and Vite.

### Compiling Production Frontend Assets
To recompile the frontend assets into `helpdesk/public/desk`:

```powershell
# Using the Frappe container
docker exec -it docker-frappe-1 bash -c "cd /home/frappe/frappe-bench/apps/helpdesk/desk && yarn build"
```

### Local Frontend Development (Hot-Reload)
If you prefer running Vite directly on your host machine:

1. Enable Yarn and install dependencies:
   ```powershell
   cd desk
   yarn install
   ```
2. Start the Vite development server:
   ```powershell
   yarn dev
   ```
   *Requests will be automatically proxied to the backend at `http://localhost:8000`.*

---

## Native Bench Setup (Alternative)

For developers running directly on a Linux/macOS host or inside WSL without Docker:

1. **Install Bench**:
   ```bash
   pip install frappe-bench
   ```
2. **Initialize Bench**:
   ```bash
   bench init --frappe-branch version-15 frappe-bench
   cd frappe-bench
   ```
3. **Get Applications**:
   ```bash
   bench get-app telephony
   bench get-app https://github.com/rajatagashe/PNG_Support_Portal.git helpdesk
   ```
4. **Create Site & Install App**:
   ```bash
   bench new-site helpdesk.localhost --admin-password admin
   bench --site helpdesk.localhost install-app telephony
   bench --site helpdesk.localhost install-app helpdesk
   bench --site helpdesk.localhost set-config developer_mode 1
   ```
5. **Start Development Server**:
   ```bash
   bench start
   ```

---

## Common Operations & Bench Commands

Execute bench commands inside the container using `docker exec`:

### Database & Cache Operations
- **Clear Site Cache**:
  ```powershell
  docker exec -it docker-frappe-1 bash -c "cd frappe-bench && bench --site helpdesk.localhost clear-cache"
  ```
- **Run Database Migrations & Patches**:
  ```powershell
  docker exec -it docker-frappe-1 bash -c "cd frappe-bench && bench --site helpdesk.localhost migrate"
  ```
- **Open Frappe Python Console**:
  ```powershell
  docker exec -it docker-frappe-1 bash -c "cd frappe-bench && bench --site helpdesk.localhost console"
  ```
- **Open MariaDB MySQL Console**:
  ```powershell
  docker exec -it docker-frappe-1 bash -c "cd frappe-bench && bench --site helpdesk.localhost mariadb"
  ```

### Running Backend Unit & Integration Tests
```powershell
docker exec -it docker-frappe-1 bash -c "cd frappe-bench && bench --site helpdesk.localhost run-tests --app helpdesk"
```

### Container Lifecycle Management
- **View Container Logs**:
  ```powershell
  docker logs -f docker-frappe-1
  ```
- **Stop Containers**:
  ```powershell
  cd docker
  docker compose stop
  ```
- **Restart Containers**:
  ```powershell
  cd docker
  docker compose up -d
  ```
- **Tear Down Containers (Preserving Database Volume)**:
  ```powershell
  cd docker
  docker compose down
  ```

---

## Project Structure

```
PNG_Support_Portal/
├── desk/                           # Vue 3 + TypeScript Frontend SPA
│   ├── src/
│   │   ├── components/             # Reusable UI components (agent desk & portal)
│   │   ├── pages/                  # Page routes (tickets, dashboard, customer portal)
│   │   ├── stores/                 # Pinia state stores
│   │   └── router/                 # Vue Router navigation definitions
│   ├── package.json                # Frontend dependencies
│   ├── vite.config.js              # Vite bundling & proxy configuration
│   └── tailwind.config.js          # Design system & semantic color tokens
├── docker/                         # Dockerized environment configuration
│   ├── docker-compose.yml          # Services definition (mariadb, redis, frappe)
│   └── init.sh                     # Container provisioning and startup script
├── helpdesk/                       # Python Backend (Frappe App)
│   ├── api/                        # Whitelisted REST endpoints (@frappe.whitelist)
│   ├── automation/                 # Event triggers & time-based automation engines
│   ├── doctype/                    # Frappe DocType definitions (schema, controllers)
│   ├── overrides/                  # Frappe core overrides (assignment, email)
│   ├── setup/                      # Fixtures, initial views, and installer scripts
│   ├── tests/                      # Automated unit and integration test suite
│   ├── hooks.py                    # Frappe app lifecycle hooks & event listeners
│   └── utils.py                    # Utility functions and permission helpers
├── realtime/                       # Real-time WebSocket handlers (Socket.IO)
├── AGENTS.md                       # Coding and architecture guidelines for AI agents
├── HELPDESK_ENHANCEMENT_PLAN.md    # Detailed specification and enhancement roadmap
├── package.json                    # Workspace root scripts
└── pyproject.toml                  # Python package configuration
```

---

## Support Mailbox Integration (Microsoft 365)

The support mailbox `support.png@amantyatech.com` is hosted on **Microsoft 365 (Exchange Online)** (MX `amantyatech-com.mail.protection.outlook.com`). Exchange Online rejects username/password (Basic auth) logins for IMAP and SMTP, and app passwords don't work for them either. So the portal connects with **OAuth 2.0 (XOAUTH2)** through an Entra ID app registration, using Frappe's built-in `Connected App` + `Email Account (auth_method = OAuth)`.

The default is **app-only access** (`MS365_AUTH_MODE=app`): the portal logs in to the mailbox as the Entra app itself, so no person ever signs in and nothing depends on one user's session. Frappe asks Microsoft for a fresh token whenever it needs one (`Email Account.backend_app_flow`), so the connection survives logouts and server restarts. The client secret is stored encrypted (Connected App, site `encryption_key`). No mailbox password is stored anywhere.

### 1. One-time Microsoft 365 setup — needs a Microsoft 365 admin

1. **Entra admin center → App registrations → your app → API permissions → + Add a permission → APIs my organization uses →** search **Office 365 Exchange Online** **→ Application permissions →** tick `IMAP.AccessAsApp` and `SMTP.SendAsApp` → **Add permissions** → **Grant admin consent**.
2. **Entra admin center → Enterprise applications →** open the same app → copy its **Object ID**. This is the enterprise application's ID, not the app registration's.
3. In **Exchange Online PowerShell** (`Install-Module ExchangeOnlineManagement`, then `Connect-ExchangeOnline`):
   ```powershell
   New-ServicePrincipal -AppId <Application (client) ID> -ObjectId <Enterprise app Object ID>
   Add-MailboxPermission -Identity "support.png@amantyatech.com" -User <Enterprise app Object ID> -AccessRights FullAccess
   Add-RecipientPermission -Identity "support.png@amantyatech.com" -Trustee <Enterprise app Object ID> -AccessRights SendAs -Confirm:$false
   ```
   This limits the app to this one mailbox.
4. **Microsoft 365 admin center → Users → support.png@amantyatech.com → Mail → Manage email apps**: keep **IMAP** on and turn **Authenticated SMTP** on.

### 2. Provision the Connected App and mailbox

Put `MS365_TENANT_ID`, `MS365_CLIENT_ID` and `MS365_CLIENT_SECRET` (the secret's **Value**, not its ID) in your local `.env`, never in `.env.example`. Then run:

```bash
# from the repo root, in Git Bash
set -a; . ./.env; set +a
docker exec -e MS365_TENANT_ID -e MS365_CLIENT_ID -e MS365_CLIENT_SECRET docker-frappe-1 bash -c "cd frappe-bench && bench --site helpdesk.localhost execute helpdesk.setup.setup_rbac.execute"
```

The script creates the `Microsoft 365 Support Mailbox` Connected App (scope `https://outlook.office365.com/.default`) and the `PNG Support Desk` Email Account (OAuth app-only, IMAP INBOX → HD Ticket), switched off. Re-running it, for example to rotate the secret, keeps an already connected mailbox on.

### 3. Activate

Log in as **Admin**, open **Support Emails**, and click **Activate** on the *Support Mailbox Connection* card. Frappe logs in over IMAP and SMTP once to prove the grants work, switches the mailbox on and runs the first sync. If Microsoft refuses the login, the card shows *"Microsoft rejected the app's access to the mailbox"* with a **Retry** button; finish step 1 and retry.

**Delegated sign-in instead:** set `MS365_AUTH_MODE=delegated`, add the delegated `IMAP.AccessAsUser.All`, `SMTP.Send` and `offline_access` permissions plus the redirect URI the script prints (a **Web** platform; Microsoft only accepts `https://` or `http://localhost`, so set `host_name`). Then click **Connect** and sign in once as the mailbox. This needs admin consent too, if your tenant blocks user consent.

### How sync works

| Piece | Behaviour |
| :--- | :--- |
| **Polling** | `scheduled_sync_support_emails` runs every minute (`* * * * *`) and pulls each support mailbox (Email Accounts whose IMAP folder or `append_to` is HD Ticket). Needs the scheduler on (`bench --site <site> enable-scheduler`) and `bench migrate` after updating, so the job is registered. |
| **Live updates** | Each received email publishes `helpdesk:support-email-received` (no email data in the event); open Support Email pages reload the list. New tickets still publish `helpdesk:new-ticket`. |
| **Duplicates** | Frappe skips mail whose `Message-ID` is already stored. A per-mailbox file lock stops the minute cron, Frappe's own 10-minute pull and **Sync now** from fetching the same mail at the same time. |
| **Errors** | Each pull records the mailbox state (`connected` / `error`) with an error kind: `app_access_denied`, `authorization_required`, `authentication_failed`, `connection_failed`, `processing_failed` or `sync_failed`. The page shows a plain message, never the raw error. Tracebacks go to the Error Log, where Frappe masks variables named like password, token, secret or key. |
| **Reconnection** | A failing mailbox is retried every 5 minutes instead of every minute. App-only mailboxes get a fresh token automatically; a delegated mailbox with an expired or revoked sign-in shows **Reconnect** to admins. |
| **Bounces / auto-replies** | Parked as Unhandled Email, as before. |

### What Support Emails shows

- List: sender name and address, subject, CGD, team, assignee, received time, status, **unread** marker and **attachment** icon. Filters by CGD, team, status and **read state**; search covers subject, sender, ticket ID and **message text**.
- **View** opens the full thread: sender, To/Cc, date and time, sanitized message body, attachments (downloaded through `support_mailbox.download_support_email_attachment`, which only serves files on support emails or their tickets), **Mark as read / unread**, and **Reply** (plain text, sent from the support mailbox and logged on the ticket).
- Opening an email marks it read. Agents can still open the full ticket; Support Email Users stay on this page.

---

## Role-Based Access Control (RBAC) Architecture

PNG Support Desk implements strict end-to-end Role-Based Access Control (RBAC) designed around two primary operational personas: **Admin** and **User (Support Email User)**. Security is enforced at both the client-side router and the server-side API layers, ensuring complete isolation without breaking existing desk features.

---

### 1. Admin Role vs. User Role

#### **Admin Role**
- **Target Persona**: System Administrators, Helpdesk Operations Managers, CGD Superusers (`Administrator`).
- **Access Level**: **Unrestricted (Full Access)** across all portal modules and data.
- **Key Capabilities**:
  - Full visibility and CRUD access to all tickets, customer organizations, contacts, and knowledge base articles.
  - Complete access to executive custom reporting (CSV, XLSX, JSON exports) and CGD entity breakdown metrics.
  - Administration of SLA service levels, holiday schedules, agent queues, skill assignments, and automation triggers.
  - System configuration, DocType schema management, user management, and telephony settings.

#### **User Role (`HD Support Email User`)**
- **Target Persona**: Dedicated Email Operations Staff, Email Triage Personnel (`support.png@amantyatech.com`).
- **Access Level**: **Restricted strictly to the Support Email Management module (`/support-emails`)**.
- **Key Capabilities**:
  - View, search, and filter inbound and outbound support communications and email chains.
  - Access email analytics dashboards (daily, weekly, monthly distribution, CGD entity breakdown, and timeline trends).
  - Inspect email message headers, sender verification status, and linked ticket associations.
  - Trigger an on-demand mailbox sync and export the email report (XLSX / CSV).
  - Open the full email thread with attachments, mark emails read/unread, and reply to the sender from the support mailbox.
- **Restrictions (Strictly Enforced)**:
  - **No Access** to Ticket Workspace (`/tickets`), Ticket Details (`/tickets/:id`), or Custom Views.
  - **No Access** to Operational Dashboard (`/home`, `/analytics`), Call Logs (`/call-logs`), or Knowledge Base (`/articles`).
  - **No Access** to Customers (`/customers`), Contacts (`/contacts`), or Settings (`/settings/*`).
  - **No Access** to Administrative Reports (`/custom-reports`) or backend export endpoints.
  - **No Reassign**: assigning tickets stays with agents, so the Reassign button is hidden.
  - Administrative menus, quick action buttons, ticket view sidebars, and global search shortcuts are hidden from the UI.
- **Not an agent**: `is_agent()` is false for this role, so every `@agent_only` endpoint returns HTTP 403. A user who also holds `Agent` or an active `HD Agent` record is treated as a normal agent.

---

### 2. Module Access Matrix

| Module / Feature | Admin Role | User Role (`HD Support Email User`) | Security Enforcement Mechanism |
| :--- | :---: | :---: | :--- |
| **Support Email Management (`/support-emails`)** | ✅ Full Access | ✅ Full Access | `@agent_or_email_user_only` on the email list, sync and export endpoints |
| **Email Analytics Dashboard & Charts** | ✅ Full Access | ✅ Full Access | `@agent_or_email_user_only` on `get_email_dashboard_analytics` |
| **Email Detail, Read/Unread & Reply** | ✅ Full Access | ✅ Full Access | `support_mailbox` endpoints with `@agent_or_email_user_only`; agents keep their ticket permissions |
| **Email Reassignment & Assignment History** | ✅ Full Access | ❌ Blocked (403) | `@agent_only` + Reassign button hidden |
| **Ticket Workspace (`/tickets`)** | ✅ Full Access | ❌ Blocked (403) | Vue Router Guard + `@agent_only` APIs + HD Ticket permission hooks |
| **Ticket Details & Editing (`/tickets/:id`)** | ✅ Full Access | ❌ Blocked (403) | Vue Router Guard + HD Ticket `has_permission` |
| **Executive Reports & Exports (`/custom-reports`)** | ✅ Full Access | ❌ Blocked (403) | Backend `@admin_only` decorator |
| **Agent Performance & Workload** | ✅ Full Access | ❌ Blocked (403) | `doc.get_list_data` rejects every DocType for this role |
| **Customer & Contact Management** | ✅ Full Access | ❌ Blocked (CGD names read-only) | Vue Router Guard; HD Customer readable for the CGD filter only |
| **Knowledge Base Articles (`/articles`)** | ✅ Full Access | ❌ Blocked | Vue Router Guard + Navigation suppressed |
| **Call Logs & Telephony (`/call-logs`)** | ✅ Full Access | ❌ Blocked | Vue Router Guard + Navigation suppressed |
| **System Settings & Triggers (`/settings/*`)** | ✅ Full Access | ❌ Blocked (403) | Backend `@admin_only` + UI suppressed |
| **User & Role Management** | ✅ Full Access | ❌ Blocked (403) | Frappe System Manager permissions |

---

### 3. Dedicated Login Flow & Post-Login Redirection

The portal features a dedicated, role-aware authentication page at `http://localhost:8000/helpdesk/login` (accessible also via `/login` within the SPA).

```
                      ┌──────────────────────────────────────────┐
                      │    Portal Login (/helpdesk/login)        │
                      │  - Quick Switcher: Admin / User Demo     │
                      │  - Form: usr + pwd                       │
                      └────────────────────┬─────────────────────┘
                                           │ POST /api/method/login
                                           ▼
                      ┌──────────────────────────────────────────┐
                      │    helpdesk.api.auth.get_user            │
                      │  Returns: role_type, is_admin,           │
                      │           is_email_user_only             │
                      └────────────────────┬─────────────────────┘
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    │                                             │
      role_type === "admin"                         role_type === "user"
                    │                                             │
                    ▼                                             ▼
       ┌────────────────────────┐                    ┌────────────────────────┐
       │   Redirect: /home      │                    │ Redirect:              │
       │   (Full Agent Portal)  │                    │ /support-emails        │
       └────────────────────────┘                    └────────────────────────┘
```

1. **Authentication**: The user logs in via credentials form or selects the 1-click credential switcher.
2. **Session Identification**: `helpdesk.api.auth.get_user` evaluates the authenticated session and returns:
   - `is_admin`: `true` for administrators; `false` for email users.
   - `is_email_user_only`: `true` when the user has only `HD Support Email User` access.
   - `role_type`: `"admin"` or `"user"`.
   - `has_desk_access`: `true`.
3. **Automated Post-Login Routing**:
   - **Admin** is directed to `/home` or `/tickets`.
   - **User** is immediately redirected to `/support-emails`.
4. **Visual Role Badge**:
   - The user menu at the bottom-left of the sidebar dynamically displays a pill badge indicating either `ADMIN` or `USER`.

---

### 4. Direct URL Protection (Frontend Guard)

Hiding navigation buttons is not sufficient for true client security. The Vue Router is configured with global navigation guards in `desk/src/router/index.ts`:

- Whenever an authenticated `User` (`isEmailUserOnly === true`) attempts to access any route other than `/support-emails`:
  1. The navigation guard intercepts the routing event before the target component renders.
  2. A notification toast is displayed:
     > *"Access Denied: Your account role is restricted to Support Email Management only."*
  3. The router automatically aborts the navigation and redirects the user back to `/support-emails`.
- Even if a user manually modifies the browser address bar to `/tickets`, `/settings`, `/customers`, or `/custom-reports`, they are immediately blocked and returned to the email management workspace.

---

### 5. Backend API Enforcement & DocType Filtering

Client-side restrictions are backed by server-side authorization in Python ([helpdesk/utils.py](helpdesk/utils.py)):

1. **Email users are not agents**: `is_agent()` only counts `Agent`, `Agent Manager`, admins and active `HD Agent` records. `is_support_email_only()` is true for a user with `HD Support Email User` who is not an agent, so every `@agent_only` endpoint and the HD Ticket permission hooks reject them.
2. **`@agent_or_email_user_only` Decorator**: The only endpoints opened to this role are `email_management.get_support_emails`, `get_email_dashboard_analytics`, `sync_support_emails`, `export_email_report_xlsx` and `export_email_report_csv`.
3. **`@admin_only` Decorator**: Placed on all custom report endpoints in `custom_reports.py` (`generate_ticket_report`, the CSV/XLSX/JSON/HTML exports, `get_cgd_entity_breakdown`, `get_hourly_ticket_heatmap`, `send_scheduled_analytics_digest`). Non-admins get `frappe.PermissionError` (HTTP 403).
4. **List Data Guard** ([helpdesk/api/doc.py](helpdesk/api/doc.py)): `get_list_data` raises `frappe.PermissionError` for every DocType when the caller is a support email user.
5. **DocType Permissions**: `setup_support_email_role()` in `helpdesk/setup/install.py` grants the role read on `HD Customer` and `HD Team` only, for the page's filters. It uses `frappe.permissions.add_permission`, which copies the DocType's standard permissions first. Inserting a lone `Custom DocPerm` row would make Frappe ignore the JSON permissions for every other role. The HD Customer hooks let the role read every customer, never write.

---

### 6. Provisioning & Testing RBAC

#### Role & Permissions
The role and its permissions are created by `after_install` on new sites and by the `helpdesk.patches.add_support_email_role` patch on existing sites (`bench migrate`). The patch also deletes the over-broad `Custom DocPerm` rows written by earlier versions of the provisioning script.

#### Account Provisioning Script
To create or reset the support users (`support.png@amantyatech.com`, `user@example.com`), the Outlook mailbox, and the passwords from `.env` / site config, run it explicitly:

```powershell
docker exec -it docker-frappe-1 bash -c "cd frappe-bench && bench --site helpdesk.localhost execute helpdesk.setup.setup_rbac.execute"
```

It resets those users' roles to `HD Support Email User` + `Desk User`. It is not run by tests or migrations.

#### Running the RBAC Unit Test Suite
The automated test suite verifies both Admin and User permission boundaries:

```powershell
docker exec docker-frappe-1 /home/frappe/frappe-bench/env/bin/python -c "import sys, os; sys.path.insert(0, '/home/frappe/frappe-bench/apps/frappe'); sys.path.insert(0, '/home/frappe/frappe-bench/apps/helpdesk'); os.chdir('/home/frappe/frappe-bench/sites'); import frappe; frappe.init(site='helpdesk.localhost'); frappe.connect(); import unittest; from helpdesk.tests.test_rbac_access_control import TestRoleBasedAccessControl; suite = unittest.TestLoader().loadTestsFromTestCase(TestRoleBasedAccessControl); res = unittest.TextTestRunner(verbosity=2).run(suite); frappe.destroy(); sys.exit(0 if res.wasSuccessful() else 1)"
```

The tests build their own users through `make_support_email_user()` in `helpdesk/test_utils.py` and validate:
- Admin keeps full access to email APIs, list data and custom reports.
- A support email user is not an agent, can use the email list and analytics, and reads (but cannot write) HD Customer.
- A support email user gets `frappe.PermissionError` from `@agent_only` APIs, `get_list_data`, ticket reassignment, custom reports and ticket reads.
- Agents (including granular tiers) who also hold the email role are not restricted.
- The permission patch restores standard DocType permissions after the old script's lone `Custom DocPerm` row.

---

## Troubleshooting & FAQs

### 1. `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`
- **Cause**: Docker Desktop is not currently running on Windows.
- **Resolution**: Launch Docker Desktop from the Start Menu and wait until the status displays "Engine running" before executing `docker compose up -d`.

### 2. Port Conflict on Port 8000 or 9000
- **Cause**: Another local web server or background process is using port `8000` or `9000`.
- **Resolution**: Identify and stop conflicting processes, or edit `docker/docker-compose.yml` to change the host port mapping (e.g., `- 8001:8000`).

### 3. Changes in DocType Not Reflecting
- **Resolution**: Execute `migrate` and clear site cache:
  ```powershell
  docker exec -it docker-frappe-1 bash -c "cd frappe-bench && bench --site helpdesk.localhost migrate && bench --site helpdesk.localhost clear-cache"
  ```

### 4. Resetting the Entire Environment
To reset the environment to a pristine state (warning: deletes all database records):
```powershell
cd docker
docker compose down -v
docker compose up -d
```

---

## License

This project is licensed under the terms described in the [LICENSE](file:///C:/Users/rajat.agashe/Desktop/PNG_Project/PNG_Support_Portal/LICENSE) file.

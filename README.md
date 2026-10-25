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
- [Role-Based Access Control (RBAC)](#role-based-access-control-rbac)
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
| **Helpdesk Single Page App** | [http://localhost:8000/helpdesk](http://localhost:8000/helpdesk) | Main agent workspace, customer portal & knowledge base |
| **Frappe Desk / Admin Login** | [http://localhost:8000/login](http://localhost:8000/login) | Standard Frappe administrative interface |
| **Realtime Service** | `ws://localhost:9000` | Live ticket updates, typing presence, collision locks |

#### Default Administrator Credentials
- **Username**: `Administrator`
- **Password**: `admin`

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

## Role-Based Access Control (RBAC)

The portal implements granular role separation tailored to enterprise support organizations and CGD tenants:

| Role | Target Persona | Permissions & Scope |
| :--- | :--- | :--- |
| **Administrator / System Manager** | System Administrators | Unrestricted system configuration, DocType schemas, and global settings. |
| **HD Team Lead / Manager** | Support Team Leads | Queue monitoring, unassigned triage, skill/capacity assignments, and analytics. |
| **HD Tier 1 Agent** | Front-line Support | Inbound intake, basic ticket responses, public comments, and self-assignment. |
| **HD Tier 2 Agent** | Senior Technical Support | Complex ticket resolution, side conversations, and problem-incident linking. |
| **HD Auditor** | Compliance & Quality Assurance | Read-only audit access across all tickets, CSAT logs, and SLA metrics. |
| **HD Customer Manager** | CGD Entity Coordinators | View all tickets raised by members of their CGD entity, submit queries, and view SLA reports. |
| **HD Customer** | End Customer / Entity Staff | View and reply only to their own raised tickets on the self-service portal. |

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

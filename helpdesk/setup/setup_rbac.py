"""Provision the PNG Support Desk accounts. Run it explicitly, it is not a patch:

bench --site <site> execute helpdesk.setup.setup_rbac.execute
"""

import os

import frappe
from frappe.utils.password import update_password

from helpdesk.setup.install import setup_support_email_role
from helpdesk.utils import SUPPORT_EMAIL_ROLE

SUPPORT_USERS = [
    {
        "email": "support.png@amantyatech.com",
        "first_name": "PNG Support",
        "last_name": "Desk",
        "username": "support_png",
    },
    {
        "email": "user@example.com",
        "first_name": "Support",
        "last_name": "User",
        "username": "support_user",
    },
]

SUPPORT_EMAIL_ID = "support.png@amantyatech.com"
MS365_APP_NAME = "Microsoft 365 Support Mailbox"
# app: the app logs in to the mailbox itself (IMAP.AccessAsApp + SMTP.SendAsApp granted in
# Exchange); delegated: an admin signs in once as the mailbox and Frappe keeps the refresh token
MS365_SCOPES = {
    "app": ("https://outlook.office365.com/.default",),
    "delegated": (
        "https://outlook.office.com/IMAP.AccessAsUser.All",
        "https://outlook.office.com/SMTP.Send",
        "offline_access",
    ),
}


def get_secret(key: str) -> str:
    """Read a secret from the environment, falling back to site config."""
    val = os.environ.get(key) or frappe.conf.get(key.lower()) or frappe.conf.get(key)
    return str(val).strip() if val else ""


def execute():
    """Set up the support email role, its users, the OAuth support mailbox and passwords."""
    setup_support_email_role()
    support_pwd = get_secret("SUPPORT_USER_PASSWORD")
    for user in SUPPORT_USERS:
        provision_support_user(user, support_pwd)

    tenant_id = get_secret("MS365_TENANT_ID")
    client_id = get_secret("MS365_CLIENT_ID")
    client_secret = get_secret("MS365_CLIENT_SECRET")
    auth_mode = get_secret("MS365_AUTH_MODE") or "app"
    if auth_mode not in MS365_SCOPES:
        frappe.throw(f"MS365_AUTH_MODE must be one of {', '.join(MS365_SCOPES)}")
    if tenant_id and client_id and client_secret:
        connected_app = provision_connected_app(tenant_id, client_id, client_secret, auth_mode)
        provision_support_email_account(connected_app, auth_mode)
    else:
        print("Skipped the support mailbox: set MS365_TENANT_ID, MS365_CLIENT_ID, MS365_CLIENT_SECRET.")

    admin_pwd = get_secret("ADMIN_PASSWORD")
    if admin_pwd:
        update_password(user="Administrator", pwd=admin_pwd)
    frappe.clear_cache()
    print("RBAC setup completed successfully.")


def provision_support_user(details: dict, password: str):
    """Create or reset a user so it holds only the support email role."""
    email = details["email"]
    if frappe.db.exists("User", email):
        user = frappe.get_doc("User", email)
    else:
        user = frappe.new_doc("User")
        user.update(details)
        user.send_welcome_email = 0
        user.user_type = "System User"
        user.flags.no_welcome_mail = True

    user.set("roles", [])
    for role in (SUPPORT_EMAIL_ROLE, "Desk User"):
        user.append("roles", {"role": role})
    user.enabled = 1
    user.save(ignore_permissions=True)
    if password:
        update_password(user=email, pwd=password)
    print(f"Configured {email}: {[r.role for r in user.roles]}")


def provision_connected_app(tenant_id: str, client_id: str, client_secret: str, auth_mode: str):
    """Create or update the Microsoft Entra OAuth app; the secret is stored encrypted."""
    name = frappe.db.get_value("Connected App", {"provider_name": MS365_APP_NAME})
    app = frappe.get_doc("Connected App", name) if name else frappe.new_doc("Connected App")
    authority = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0"
    app.update(
        {
            "provider_name": MS365_APP_NAME,
            "client_id": client_id,
            "client_secret": client_secret,
            "authorization_uri": f"{authority}/authorize",
            "token_uri": f"{authority}/token",
        }
    )
    app.set("scopes", [{"scope": scope} for scope in MS365_SCOPES[auth_mode]])
    app.save(ignore_permissions=True)

    if auth_mode == "delegated":
        print(f"Register this redirect URI in the Entra app: {app.redirect_uri}")
        if not app.redirect_uri.startswith(("https://", "http://localhost")):
            print("Microsoft only accepts https:// or http://localhost redirect URIs; set host_name.")
    return app


def provision_support_email_account(connected_app, auth_mode: str):
    """Create or update the support mailbox as an OAuth account, switched off.

    Saving an enabled account makes Frappe log in, which needs Exchange access (app)
    or the one-time sign-in (delegated). An admin then activates it from Support Emails.
    """
    if frappe.db.exists("Email Account", {"email_id": SUPPORT_EMAIL_ID}):
        account = frappe.get_doc("Email Account", {"email_id": SUPPORT_EMAIL_ID})
    else:
        account = frappe.new_doc("Email Account")
        account.update(
            {
                "email_account_name": "PNG Support Desk",
                "email_id": SUPPORT_EMAIL_ID,
                "service": "Outlook.com",
                "track_email_status": 1,
                "create_contact": 1,
                "email_sync_option": "ALL",
                "initial_sync_count": 100,
            }
        )

    switching_mode = account.is_new() or account.auth_method != "OAuth" or bool(
        account.backend_app_flow
    ) != (auth_mode == "app")
    account.update(
        {
            "auth_method": "OAuth",
            "connected_app": connected_app.name,
            "backend_app_flow": 1 if auth_mode == "app" else 0,
            "email_server": "outlook.office365.com",
            "incoming_port": 993,
            "use_imap": 1,
            "use_ssl": 1,
            "smtp_server": "smtp.office365.com",
            "smtp_port": 587,
            "use_tls": 1,
            "append_to": "HD Ticket",
        }
    )
    if auth_mode == "app":
        # the app has no user; a stale delegated signer would mislead the status
        account.connected_user = None
    # an enabled save logs in, so keep it off until Activate / Connect proves it can;
    # a mailbox already connected this way stays on when the script is re-run
    if switching_mode or not account.has_oauth_token():
        account.update({"enable_incoming": 0, "enable_outgoing": 0})
    if not any(f.folder_name == "INBOX" for f in account.imap_folder):
        account.append("imap_folder", {"folder_name": "INBOX", "append_to": "HD Ticket"})
    account.save(ignore_permissions=True)
    next_step = "Activate" if auth_mode == "app" else "Connect"
    print(f"Configured Email Account {SUPPORT_EMAIL_ID} (OAuth, {auth_mode}). Use {next_step} on Support Emails.")

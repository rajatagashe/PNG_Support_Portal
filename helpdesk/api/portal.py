# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from helpdesk.utils import get_customers


@frappe.whitelist(allow_guest=True)
def get_portal_branding():
    """Return dynamic multi-tenant CGD branding for customer portal pages."""
    user = frappe.session.user

    default_brand = frappe.db.get_single_value("HD Settings", "brand_name") or "MyPNG Support Desk"
    default_logo = frappe.db.get_single_value("HD Settings", "brand_logo")

    if not user or user == "Guest":
        return {
            "is_customer": False,
            "customer": None,
            "customer_name": None,
            "brand_name": default_brand,
            "brand_logo": default_logo,
            "domain": None,
            "banner_title": "City Gas Distribution (CGD) Support Hub",
            "banner_subtitle": "Unified customer self-service, issue reporting, and knowledge repository.",
            "is_vip": False,
        }

    # Find customer for the logged-in user
    customer_name = None
    customers = get_customers(user=user)
    if customers:
        customer_name = customers[0]
    else:
        # Check by Contact email
        contact = frappe.db.get_value("Contact", {"email_id": user}, "name")
        if contact:
            cust_matches = get_customers(contact=contact)
            if cust_matches:
                customer_name = cust_matches[0]

    if customer_name and frappe.db.exists("HD Customer", customer_name):
        c_doc = frappe.get_doc("HD Customer", customer_name)
        return {
            "is_customer": True,
            "customer": c_doc.name,
            "customer_name": c_doc.customer_name or c_doc.name,
            "brand_name": f"{c_doc.customer_name} Support Portal",
            "brand_logo": c_doc.image or default_logo,
            "domain": c_doc.domain,
            "banner_title": f"{c_doc.customer_name} Customer Support Portal",
            "banner_subtitle": f"Official support desk and service inquiries for {c_doc.customer_name}.",
            "is_vip": bool(c_doc.get("is_vip")),
            "vip_priority": c_doc.get("vip_priority") or "Urgent",
        }

    return {
        "is_customer": False,
        "customer": None,
        "customer_name": None,
        "brand_name": default_brand,
        "brand_logo": default_logo,
        "domain": None,
        "banner_title": "City Gas Distribution (CGD) Support Hub",
        "banner_subtitle": "Unified customer self-service, issue reporting, and knowledge repository.",
        "is_vip": False,
    }


@frappe.whitelist(allow_guest=True)
def get_portal_cgd_entities():
    """Return public list of active CGD entities for multi-tenant portal directory."""
    customers = frappe.get_all(
        "HD Customer",
        fields=["name", "customer_name", "image", "domain", "is_vip"],
        order_by="customer_name asc",
        limit=50,
    )
    return customers

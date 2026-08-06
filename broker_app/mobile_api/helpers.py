import frappe
from frappe import _


def get_linked_supplier(user=None):
    """Supplier linked to this user via the Supplier's Portal Users table, or None."""
    user = user or frappe.session.user

    if user in ("Administrator", "Guest"):
        return None

    return frappe.db.get_value(
        "Portal User",
        {"user": user, "parenttype": "Supplier", "parentfield": "portal_users"},
        "parent",
        order_by="creation asc",
    )


def get_linked_supplier_or_raise(user=None):
    supplier = get_linked_supplier(user)
    if not supplier:
        frappe.throw(
            _("No Supplier is linked to this user. Please contact the administrator."),
            frappe.PermissionError,
        )
    return supplier


def is_internal_user(user=None):
    """Users not restricted to a single linked Supplier.

    Brokers log in as portal accounts (User.user_type == "Website User").
    Internal ERP staff are Desk ("System User") accounts. Some internal staff
    are *also* added to a Supplier's Portal Users table (e.g. for testing),
    which would otherwise make a real internal user look like a broker — so
    user_type, not role membership, is the source of truth here.
    """
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    return frappe.db.get_value("User", user, "user_type") == "System User"


def get_supplier_scoped_permission_query_conditions(user=None):
    """permission_query_conditions hook: restricts list/report queries to the
    caller's linked Supplier. Only kicks in for users who are actually linked
    to a Supplier as a Portal User (i.e. brokers) — everyone else (internal
    staff, System Managers) is left to the standard role-based permissions."""
    user = user or frappe.session.user

    if is_internal_user(user):
        return ""

    supplier = get_linked_supplier(user)
    if not supplier:
        return ""

    return f"`supplier` = {frappe.db.escape(supplier)}"


def has_supplier_scoped_permission(doc, ptype=None, user=None):
    """has_permission hook: guards direct single-document access (e.g. by
    name/URL) the same way get_supplier_scoped_permission_query_conditions
    guards list queries."""
    user = user or frappe.session.user

    if is_internal_user(user):
        return True

    supplier = get_linked_supplier(user)
    if not supplier:
        return True

    return doc.get("supplier") == supplier

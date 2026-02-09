import frappe
from frappe import _

def update_supplier_quotation_status(doc, method):
    for item in doc.items:
        if item.supplier_quotation:
            sq = frappe.get_doc("Supplier Quotation", item.supplier_quotation)
            if sq.workflow_state != "Converted to PO":
                sq.workflow_state = "Converted to PO"
                sq.db_update()





def validate_freight_rules(doc, method=None):
    # Apply only when Freight is Exclusive
    if doc.custom_freight != "Exclusive":
        return

    # Apply only for Admin / System Manager
    if not (frappe.session.user == "Administrator" or frappe.session.user == "System Manager"):
        return

    # Mandatory check
    if not doc.custom_transporter_supplier_:
        frappe.throw(
            "🚚 <b>Transporter Supplier is mandatory</b><br>"
            "Please select a Transporter Supplier when Freight is <b>Exclusive</b>.",
            title="Missing Transporter Supplier"
        )

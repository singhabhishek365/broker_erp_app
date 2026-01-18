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
    if doc.custom_freight == "Exclusive":
        if not doc.custom_loading_charges or doc.custom_loading_charges <= 0:
            frappe.throw("Loading Charges must be greater than 0 when Freight = Exclusive")
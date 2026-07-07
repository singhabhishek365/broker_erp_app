import frappe
from frappe.utils import nowdate, flt
from frappe.model.mapper import get_mapped_doc


def handle_workflow_po_creation(doc, method=None):
    if doc.custom_po_created:
        return

    if doc.workflow_state != "Converted to PO":
        return

    if doc.custom_freight == "Inclusive":
        create_material_po(doc)
    else:
        create_material_po(doc)
        create_transport_po(doc)

    doc.custom_po_created = 1
    doc.db_update()


def _get_incoterm_for_freight(freight_type):
    """Single source of truth for incoterm lookup, shared by material + transport POs."""
    flag = 1 if freight_type == "Exclusive" else 0
    incoterm = frappe.db.get_value(
        "Incoterm",
        {"custom_shortage_debit_to_transporter": flag},
        "name",
        order_by="creation asc"
    )
    if not incoterm:
        frappe.throw("No suitable Incoterm found")
    return incoterm


def create_material_po(quotation):
    try:
        frappe.logger("broker_po").info(f"Creating PO for SQ: {quotation.name}")

        po = get_mapped_doc(
            "Supplier Quotation",
            quotation.name,
            {
                "Supplier Quotation": {
                    "doctype": "Purchase Order",
                    "field_map": {
                        "name": "supplier_quotation",
                    },
                    "validation": {
                        "docstatus": ["=", 1]
                    }
                },
                "Supplier Quotation Item": {
                    "doctype": "Purchase Order Item",
                    "field_map": {
                        "name": "supplier_quotation_item",
                        "parent": "supplier_quotation",
                    },
                    "condition": lambda item: item.item_group != "Services",
                }
            }
        )

        po.transaction_date = nowdate()
        po.schedule_date = nowdate()
        po.validity_date = quotation.valid_till or nowdate()
        po.incoterm = _get_incoterm_for_freight(quotation.custom_freight)
        po.branch = quotation.branch
        po.taxes_and_charges = quotation.taxes_and_charges
        po.cost_center = quotation.cost_center

        for item in po.items:
            item.schedule_date = nowdate()
            item.branch = quotation.branch

        po.insert(ignore_permissions=True)

        quotation.db_set("custom_material_purchase_order_reference_", po.name, update_modified=False)

        frappe.logger("broker_po").info(f"PO Inserted (Draft): {po.name}")
        frappe.msgprint(f"Material Purchase Order Created (Draft): <b>{po.name}</b>")

        return po

    except Exception:
        frappe.log_error(
            title="Material PO Creation Failed",
            message=frappe.get_traceback()
        )
        frappe.throw("Failed to create Material Purchase Order. Check the Error Log for details.")


def create_transport_po(quotation):
    if not quotation.get("custom_transporters"):
        frappe.throw("No Transporters added in the Supplier Quotation.")

    transport_item = get_transport_service_item(quotation)

    if not transport_item:
        frappe.throw("No Freight Service Item found in Item Master")

    incoterm = _get_incoterm_for_freight(quotation.custom_freight)

    created_pos = []
    failed_rows = []

    for row in quotation.custom_transporters:
        if not row.transporter:
            continue

        try:
            if not row.rate_per_unit:
                frappe.throw(f"Rate per unit missing for Transporter <b>{row.transporter}</b> (Row #{row.idx}).")
            if not row.qty:
                frappe.throw(f"Quantity missing for Transporter <b>{row.transporter}</b> (Row #{row.idx}).")

            po = frappe.new_doc("Purchase Order")
            po.company = quotation.company
            po.supplier = row.transporter
            po.custom_is_transporter_po = 1
            po.transaction_date = nowdate()
            po.schedule_date = nowdate()
            po.validity_date = quotation.valid_till or nowdate()
            po.incoterm = incoterm
            po.branch = quotation.branch
            po.cost_center = quotation.cost_center
            po.ref_sq = quotation.name

            po.append("items", {
                "item_code": transport_item.name,
                "item_name": transport_item.item_name,
                "description": f"Transport Charges for {quotation.name} (Transporter: {row.transporter})",
                "qty": flt(row.qty),
                "rate": flt(row.rate_per_unit),
                "uom": transport_item.stock_uom,
                "schedule_date": nowdate(),
                "branch": quotation.branch,
            })

            po.insert(ignore_permissions=True)

            row.db_set("transporter_po_reference", po.name, update_modified=False)
            created_pos.append(po.name)

            frappe.logger("broker_po").info(f"Transport PO Created (Draft): {po.name} for {row.transporter}")

        except Exception:
            frappe.log_error(
                title="Transport PO Creation Failed",
                message=frappe.get_traceback()
            )
            failed_rows.append(f"{row.transporter} (Row #{row.idx})")

    if created_pos:
        po_links = ", ".join(f"<b>{p}</b>" for p in created_pos)
        frappe.msgprint(f"Transport Purchase Order(s) Created (Draft): {po_links}")

    if failed_rows:
        frappe.throw(
            "Failed to create Transport PO for: " + ", ".join(failed_rows) +
            ". Check the Error Log for details."
        )


def get_transport_service_item(quotation, price_list=None):
    price_list = price_list or frappe.db.get_single_value("Buying Settings", "buying_price_list") or "Standard Buying"

    item = frappe.db.get_value(
        "Item",
        {
            "item_group": "Services",
            "is_purchase_item": 1,
            "disabled": 0
        },
        ["name", "item_name", "stock_uom"],
        as_dict=True,
        order_by="creation"
    )

    if not item:
        frappe.throw("No active Service Item found in Item Master")

    return item
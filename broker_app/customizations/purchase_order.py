import frappe
from frappe.utils import nowdate
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
        # create_transport_pos(doc)

    doc.custom_po_created = 1
    doc.db_update()


def create_material_po(quotation):
    try:
        frappe.logger("broker_po").info(f"Creating PO for SQ: {quotation.name}")

        # Determined from the source quotation's own items (before mapping)
        # since the "Services" item-group filter below needs it.
        material_requests = {item.material_request for item in quotation.items if item.material_request}
        is_professional_service = bool(material_requests) and frappe.db.exists(
            "Material Request",
            {"name": ["in", list(material_requests)], "custom_request_category": "Professional Service"},
        )

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
                    # "Services" items are normally excluded here — they go
                    # through the separate transport-PO path — except when
                    # the quotation is Professional-Service-sourced, where
                    # the service items themselves ARE the PO's content.
                    "condition": lambda item: is_professional_service or item.item_group != "Services",
                }
            }
        )

        # Overrides / fields not carried by mapper
        po.transaction_date = nowdate()
        po.schedule_date = nowdate()
        po.validity_date = quotation.valid_till or nowdate()

        if is_professional_service:
            po.custom_purchase_type = 'Service'
            po.custom_service_subtype = 'Maintenance'
        else:
            po.custom_purchase_type = 'Material'
        # if quotation.custom_freight == "Exclusive":
        #     incoterm = frappe.db.get_value(
        #             "Incoterm",
        #             {"custom_shortage_debit_to_transporter": 1},
        #             "name",
        #             order_by="creation asc"
        #         )
        # else:
        #     incoterm = frappe.db.get_value(
        #         "Incoterm",
        #         {"custom_shortage_debit_to_transporter": 0},
        #         "name",
        #         order_by="creation asc"
        #     )

        # if not incoterm:
        #     frappe.throw("No suitable Incoterm found")

        # po.incoterm = incoterm
        po.incoterm = quotation.incoterm
        po.branch = quotation.branch
        po.taxes_and_charges = quotation.taxes_and_charges
        po.cost_center = quotation.cost_center

        for item in po.items:
            item.schedule_date = nowdate()
            item.branch = quotation.branch
            if item.material_request:
                wip_composite_asset = frappe.db.get_value("Material Request Item",{"parent": item.material_request,"item_code": item.item_code},"wip_composite_asset")
                if wip_composite_asset:
                    item.wip_composite_asset = wip_composite_asset


        po.insert(ignore_permissions=True)
        # stays as draft — no submit()

        quotation.db_set("custom_material_purchase_order_reference_", po.name, update_modified=False)

        po_label = "Service Purchase Order" if is_professional_service else "Material Purchase Order"
        frappe.logger("broker_po").info(f"PO Inserted (Draft): {po.name}")
        frappe.msgprint(f"{po_label} Created (Draft): <b>{po.name}</b>")

        return po

    except Exception as e:
        frappe.log_error(
            title="Material PO Creation Failed",
            message=frappe.get_traceback()
        )
        frappe.throw(f"Failed to create Purchase Order: {str(e)}")


def create_transport_pos(quotation):
    if not quotation.custom_transporters:
        frappe.throw("At least one Transporter row is required when Freight is Exclusive")

    po_names = []
    for row in quotation.custom_transporters:
        po_names.append(create_transport_po_for_row(quotation, row))

    if po_names:
        # Kept for backward compatibility with existing consumers (e.g. Gate
        # Entry's PO -> Supplier Quotation lookup) that read the single field.
        quotation.db_set("custom_transporter_purchase_order_reference_", po_names[0], update_modified=False)
        quotation.db_set("custom_transporter_supplier", quotation.custom_transporters[0].transporter, update_modified=False)

    return po_names


def create_transport_po_for_row(quotation, row):
    try:
        frappe.logger("broker_po").info(f"Transport PO Trigger for {quotation.name} (Transporter row #{row.idx})")

        transport_item = get_transport_service_item(row)

        if not transport_item:
            frappe.throw("No Freight Service Item found in Item Master")

        po = frappe.new_doc("Purchase Order")
        po.company = quotation.company
        po.supplier = row.transporter
        po.custom_purchase_type = 'Service'
        po.custom_service_subtype = 'Logistics/Transport'
        po.custom_transporter_for = 'Supplier'
        po.custom_is_transporter_po = 1
        po.custom_material_po = quotation.custom_material_purchase_order_reference_
        po.transaction_date = nowdate()
        po.schedule_date = nowdate()
        po.validity_date = quotation.valid_till or nowdate()
        # if quotation.custom_freight == "Exclusive":
        #     incoterm = frappe.db.get_value(
        #             "Incoterm",
        #             {"custom_shortage_debit_to_transporter": 1},
        #             "name",
        #             order_by="creation asc"
        #         )
        # else:
        #     incoterm = frappe.db.get_value(
        #         "Incoterm",
        #         {"custom_shortage_debit_to_transporter": 0},
        #         "name",
        #         order_by="creation asc"
        #     )

        # if not incoterm:
        #     frappe.throw("No suitable Incoterm found")

        # po.incoterm = incoterm
        po.incoterm = quotation.incoterm
        po.branch = quotation.branch
        po.cost_center = quotation.cost_center
        po.ref_sq = quotation.name

        # -------------------------
        # SERVICE ITEM ENTRY
        # -------------------------
        po.append("items", {
            "item_code": transport_item.name,
            "item_name": transport_item.item_name,
            "description": f"Transport Charges for {quotation.name} (Row #{row.idx})",
            "qty": row.qty or quotation.items[0].qty,
            "rate": row.rate_per_unit,
            "uom": transport_item.stock_uom,
            "schedule_date": nowdate(),
            "branch": quotation.branch,
        })

        po.insert(ignore_permissions=True)
        # stays as draft — no submit()

        frappe.db.set_value("Supplier Quotation Transporter", row.name, "transporter_po_reference", po.name)

        frappe.logger("broker_po").info(f"Transport PO Created (Draft): {po.name}")
        frappe.msgprint(f" Transport Purchase Order Created (Draft) for {row.transporter}: <b>{po.name}</b>")

        return po.name

    except Exception as e:
        frappe.logger("broker_po").error(f"Transport PO Failed: {str(e)}")
        frappe.throw(f"Failed to create Transport Purchase Order for {row.transporter}: {str(e)}")

def get_transport_service_item(row, price_list=None):
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

    if not row.rate_per_unit:
        frappe.throw(f"Rate Per Unit is missing for Transporter row #{row.idx}")

    item.rate = row.rate_per_unit
    return item


# def get_freight_account(company=None):
#     # Use company of the PO if passed
#     if not company:
#         company = frappe.defaults.get_global_default("company")
    
#     # Try to get existing Freight account in this company
#     account = frappe.db.get_value(
#         "Account",
#         {"account_name": "Freight and Forwarding Charges", "company": company},
#         "name"
#     )
    
#     if not account:
#         # If missing, create it
#         account = frappe.get_doc({
#             "doctype": "Account",
#             "account_name": "Freight and Forwarding Charges",
#             "company": company,
#             "account_type": "Expense",
#             "root_type": "Expense",
#             "is_group": 0
#         }).insert(ignore_permissions=True).name

#     return account


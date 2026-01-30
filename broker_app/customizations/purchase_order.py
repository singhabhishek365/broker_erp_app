import frappe
from frappe.utils import nowdate

def handle_workflow_po_creation(doc, method=None):
    frappe.logger("broker_po").info("Workflow Triggered")
    frappe.logger("broker_po").info(f"Workflow State: {doc.workflow_state}")
    frappe.log_error(
    title="Test PO Debug",
    message=f"Transport Item: {doc}"
)

    # Ensure workflow reached Approved state
    if doc.workflow_state != "Converted to PO":
        return
   

    # Create PO(s)
    if doc.custom_freight == "Inclusive":
        create_material_po(doc)
    else:
        create_material_po(doc)
        create_transport_po(doc)

    # mark flag
    doc.custom_po_created = 1
    doc.db_update()


def create_material_po(quotation):
    try:
        frappe.logger().info(f"Creating PO for SQ: {quotation.name}")

        po = frappe.new_doc("Purchase Order")
        po.supplier = quotation.supplier
        po.supplier_quotation = quotation.name
        
        # VERY IMPORTANT — use quotation company
        po.company = quotation.company
        
        po.transaction_date = nowdate()
        po.schedule_date = nowdate()

        for item in quotation.items:
             if  item.item_group == "Services":
               continue
             po.append("items", {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "description": item.description,
                "qty": item.qty,
                "rate": item.rate,
                "uom": item.uom,
                "schedule_date": nowdate(),
                "supplier_quotation": quotation.name,
                "supplier_quotation_item": item.name
                
            })

        po.insert(ignore_permissions=True)

        frappe.logger().info(f"PO Inserted Successfully: {po.name}")

        po.submit()

        frappe.msgprint(f"Material Purchase Order Created: <b>{po.name}</b>")
        frappe.logger().info(f"PO Submitted Successfully: {po.name}")

        return po

    except Exception as e:
        frappe.log_error(
            title="Material PO Creation Failed",
            message=frappe.get_traceback()
        )
        frappe.logger().error(f"PO Creation Failed: {str(e)}")
        frappe.throw(f"Failed to create Purchase Order: {str(e)}")






def create_transport_po(quotation):
    try:
        frappe.logger("broker_po").info(f"Transport PO Trigger for {quotation.name}")

        # -------------------------
        # VALIDATIONS
       

        # Transport Item from Quotation
        transport_item = None
        # for item in quotation.items:
        #     if item.item_group == "Services":      # Your rule
        #         transport_item = item
        #         break
        
        transport_item =  get_transport_service_item()
        frappe.log_error(
            title="Broker PO Debug",
            message=f"Transport Item: {transport_item}"
        )
        if not transport_item:
            frappe.throw("No Freight Service Item found in Supplier Quotation")

        if not transport_item.rate:
            frappe.throw("Freight Item Rate is missing")

       # loading_charges = float(transport_item.rate or 0)



        # -------------------------
        # CREATE TRANSPORT PO
        # -------------------------
        po = frappe.new_doc("Purchase Order")
        po.company =quotation.company
        po.supplier = quotation.supplier
        po.supplier_quotation = quotation.name
        po.transaction_date = nowdate()
        po.schedule_date = nowdate()

        # -------------------------
        # SERVICE ITEM ENTRY
        # -------------------------
        po.append("items", {
            "item_code": transport_item.item_name,
            "item_name": transport_item.item_name,
            "description": f"Transport Charges for {quotation.name}",
            "qty": 1,
            "rate": transport_item.rate,
            "uom": transport_item.stock_uom,
            "schedule_date": nowdate(),

            # 🔗 ensure linking appears in "Connections"
            "supplier_quotation": quotation.name
        })

        po.insert(ignore_permissions=True)
        po.submit()

        frappe.logger("broker_po").info(f"Transport PO Created: {po.name}")
        frappe.msgprint(f"🚚 Transport Purchase Order Created: <b>{po.name}</b>")

        return po.name

    except Exception as e:
        frappe.logger("broker_po").error(f"Transport PO Failed: {str(e)}")
        frappe.msgprint(f"<b>Transport PO Failed!</b><br>{str(e)}", indicator="red")
        raise



# def get_transport_service_item():
#     item = frappe.db.get_value(
#         "Item",
#         {
#             "item_group": "Services",
#             "is_purchase_item": 1,
#             "disabled": 0
#         },
#         ["name", "item_name", "stock_uom" , "rate"],
#         as_dict=True
#     )

#     if not item:
#         frappe.throw("No active Service Item found in Item Master")

#     return item

def get_transport_service_item(price_list="Standard Buying"):
    item = frappe.db.get_value(
        "Item",
        {
            "item_group": "Services",
            "is_purchase_item": 1,
            "disabled": 0
        },
        ["name", "item_name", "stock_uom"],
        as_dict=True
    )

    if not item:
        frappe.throw("No active Service Item found in Item Master")

    rate = frappe.db.get_value(
        "Item Price",
        {
            "item_code": item.name,
            "price_list": price_list
        },
        "price_list_rate"
    )

    item.rate = rate or 0
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


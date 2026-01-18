import frappe
import json


@frappe.whitelist()
def create_broker(
    broker_name,
    item_name,
    item_rate,
    taxes,
    vehicle_number
):
    try:
        doc = frappe.get_doc({
            "doctype": "Broker",
            "broker_name": broker_name,
            "item_name": item_name,
            "item_rate": item_rate,
            "taxes": taxes,
            "vehicle_number": vehicle_number
        })

        doc.insert()
        doc.submit()

        return {
            "success": True,
            "message": "Broker created and submitted successfully",
            "data": {
                "name": doc.name,
                "docstatus": doc.docstatus
            }
        }

    except frappe.PermissionError:
        return {
            "success": False,
            "message": "Permission denied"
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Create Broker API Error")
        return {
            "success": False,
            "message": str(e)
        }
        

@frappe.whitelist()
def get_brokers(page=1, page_size=10):
    try:
        page = int(page)
        page_size = int(page_size)

        start = (page - 1) * page_size

        brokers = frappe.get_list(
            "Broker",
            fields=[
                "name",
                "broker_name",
                "item_name",
                "item_rate",
                "taxes",
                "vehicle_number",
                "docstatus",
                "creation"
            ],
            limit_start=start,
            limit_page_length=page_size,
            order_by="creation desc"
        )

        total_count = frappe.db.count("Broker")

        return {
            "success": True,
            
            "message": "Brokers fetched successfully",
           
            "data": brokers,
             "pagination": {
                "page": page,
                "page_size": page_size,
                "total_records": total_count,
                "total_pages": (total_count + page_size - 1) // page_size
            }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Broker List API Error")
        return {
            "success": False,
            "message": str(e)
        }




@frappe.whitelist()
def get_supplier_quotations(filters=None, fields=None, start=0, page_length=20):
    try:
        if not frappe.has_permission("Supplier Quotation", "read"):
            frappe.throw(_("Insufficient permissions"))

        # Parse JSON inputs
        if isinstance(filters, str):
            filters = frappe.parse_json(filters)

        if isinstance(fields, str):
            fields = frappe.parse_json(fields)

        # Parent fields ONLY
        parent_fields = [
            "name", "supplier", "supplier_name", "transaction_date",
            "custom_distance_in_km_", "custom_freight", "custom_remarks",
            "workflow_state", "valid_till", "grand_total"
        ]

        # -----------------------------
        # 1️⃣ Fetch Supplier Quotations
        # -----------------------------
        quotations = frappe.get_list(
            "Supplier Quotation",
            filters=filters or {},
            fields=parent_fields,
            start=start,
            page_length=page_length,
            order_by="transaction_date desc"
        )

        if not quotations:
            return {
                "success": True,
                "data": [],
                "total_count": 0
            }

        quotation_names = [q.name for q in quotations]

        # -----------------------------
        # 2️⃣ Fetch ALL items in one query
        # -----------------------------
        items = frappe.get_all(
            "Supplier Quotation Item",
            filters={"parent": ["in", quotation_names]},
            fields=[
                "parent", "item_code", "item_name",
                "qty", "rate", "amount", "uom"
            ]
        )

        # -----------------------------
        # 3️⃣ Map items → quotations
        # -----------------------------
        item_map = {}
        for item in items:
            item_map.setdefault(item.parent, []).append(item)

        for q in quotations:
            q["items"] = item_map.get(q.name, [])

        # -----------------------------
        # 4️⃣ Total Count
        # -----------------------------
        total_count = frappe.db.count(
            "Supplier Quotation",
            filters=filters or {}
        )

        return {
            "success": True,
            "data": quotations,
            "total_count": total_count,
            "page_length": page_length,
            "start": start
        }

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Get Supplier Quotations Error"
        )
        return {
            "success": False,
            "message": _("Something went wrong")
        }




@frappe.whitelist()
def create(**data):
    try:
        # -------------------------
        # VALIDATIONS
        # -------------------------
        
       
        required_fields = [
            "supplier",
            "custom_freight",
            "items"
        ]

        for field in required_fields:
            if not data.get(field):
                frappe.throw(_(f"{field.replace('_', ' ').title()} is mandatory"))

        if not isinstance(data.get("items"), list) or len(data["items"]) == 0:
            frappe.throw(_("At least one item is required"))

        # -------------------------
        # CREATE DOCUMENT
        # -------------------------
        sq = frappe.new_doc("Supplier Quotation")
        sq.supplier = data["supplier"]
        sq.transaction_date = data.get("transaction_date")
        sq.valid_till = data.get("valid_till")

        # Custom fields
        sq.custom_freight = data["custom_freight"]
        sq.custom_loading_charges = data["custom_loading_charges"]
        sq.custom_remarks = data.get("custom_remarks")
        sq.custom_distance_in_km_ = data.get("custom_distance_in_km_")
        sq.custom_location = data.get("custom_location")

        # -------------------------
        # ITEMS
        # -------------------------
        for item in data["items"]:
            sq.append("items", {
                "item_code": item["item_code"],
                "qty": item.get("qty", 1),
                "rate": item.get("rate", 0),
                "uom": item.get("uom", "Nos")
            })

        sq.insert(ignore_permissions=True)

        if data.get("submit"):
            sq.submit()

        return {
            "success": True,
            "message": "Supplier Quotation created",
            "data": {
                "name": sq.name,
                "grand_total": sq.grand_total,
                "status": sq.workflow_state
            }
        }

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Mobile SQ Create API")
        return {
            "success": False,
            "message": "Failed to create Supplier Quotation"
        }



@frappe.whitelist()
def get_purchase_orders(filters=None, fields=None, start=0, page_length=20):
    """
    Fetch Purchase Orders with items
    
    Args:
        filters: JSON string or dict of filters
        fields: JSON string or list of fields (optional)
        start: Starting index for pagination
        page_length: Number of records per page
        
    Returns:
        dict: Success response with purchase orders and items
    """
    try:
        # Check permissions
        if not frappe.has_permission("Purchase Order", "read"):
            frappe.throw(_("Insufficient permissions"))

        # Parse JSON inputs
        if isinstance(filters, str):
            filters = frappe.parse_json(filters)

        if isinstance(fields, str):
            fields = frappe.parse_json(fields)

        # Define parent fields
        parent_fields = [
            "name",
            "supplier",
            "supplier_name",
            "order_confirmation_no",
            "transaction_date",
            "schedule_date",
            "apply_tds",
            "is_subcontracted",
            "currency",
            "price_list_currency",
            "total_qty",
            "total",
            "total_taxes_and_charges",
            "grand_total",
            "status",
            "workflow_state",
            "creation",
            "modified"
        ]

        # -----------------------------
        # 1️⃣ Fetch Purchase Orders
        # -----------------------------
        purchase_orders = frappe.get_list(
            "Purchase Order",
            filters=filters or {},
            fields=parent_fields,
            start=start,
            page_length=page_length,
            order_by="transaction_date desc"
        )

        if not purchase_orders:
            return {
                "success": True,
                "data": [],
                "total_count": 0,
                "page_length": page_length,
                "start": start
            }

        po_names = [po.name for po in purchase_orders]

        # -----------------------------
        # 2️⃣ Fetch ALL items in one query
        # -----------------------------
        items = frappe.get_all(
            "Purchase Order Item",
            filters={"parent": ["in", po_names]},
            fields=[
                "parent",
                "item_code",
                "item_name",
                "description",
                "schedule_date",
                "qty",
                "uom",
                "rate",
                "amount",
                "warehouse",
                "stock_uom",
                "conversion_factor"
            ]
        )

        # -----------------------------
        # 3️⃣ Map items to purchase orders
        # -----------------------------
        item_map = {}
        for item in items:
            item_map.setdefault(item.parent, []).append(item)

        for po in purchase_orders:
            po["items"] = item_map.get(po.name, [])

        # -----------------------------
        # 4️⃣ Get total count
        # -----------------------------
        total_count = frappe.db.count(
            "Purchase Order",
            filters=filters or {}
        )

        return {
            "success": True,
            "data": purchase_orders,
            "total_count": total_count,
            "page_length": page_length,
            "start": start,
            "message": "Purchase Orders fetched successfully"
        }

    except frappe.PermissionError:
        frappe.log_error(
            frappe.get_traceback(),
            "Get Purchase Orders Permission Error"
        )
        return {
            "success": False,
            "message": "Permission denied"
        }

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            "Get Purchase Orders Error"
        )
        return {
            "success": False,
            "message": str(e)
        }
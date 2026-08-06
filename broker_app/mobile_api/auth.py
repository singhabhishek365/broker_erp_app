import frappe
from frappe.auth import LoginManager

from broker_app.mobile_api.helpers import get_linked_supplier

@frappe.whitelist(allow_guest=True)
def login(email, password):

    try:
        # Authenticate
        lm = LoginManager()
        lm.authenticate(user=email, pwd=password)
        lm.post_login()

        user = frappe.get_doc("User", email)

        # Generate API Key
        if not user.api_key:
            user.api_key = frappe.generate_hash(length=15)

        # Generate API Secret (ONLY if missing)
        if not user.api_secret:
            api_secret = frappe.generate_hash(length=15)
            user.api_secret = api_secret
        else:
            api_secret = user.get_password("api_secret")

        user.save(ignore_permissions=True)

        # Supplier linked to this user (Broker == Supplier + Portal User)
        supplier = get_linked_supplier(user.name)
        supplier_name = (
            frappe.db.get_value("Supplier", supplier, "supplier_name") if supplier else None
        )

        return {
            "status": 200,
            "success": True,
            "message": "Login successful",
            "data": {
                "user": user.name,
                "full_name": user.full_name,
                "api_key": user.api_key,
                "api_secret": api_secret,
                "supplier": supplier,
                "supplier_name": supplier_name
            }
        }

    except frappe.AuthenticationError:
        frappe.clear_messages()
        return {
            "status": 401,
            "success": False,
            "message": "Invalid login credentials"
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Login API Error")
        return {
            "status": 500,
            "success": False,
            "message": str(e)
        }

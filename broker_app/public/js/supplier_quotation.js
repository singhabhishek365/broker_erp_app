frappe.ui.form.on("Supplier Quotation", {
	onload(frm) {
		frm.set_query("custom_party_name_", () => ({
			filters: { custom_is_party: 1 },
		}));

		frm.set_query("custom_transporter_supplier", () => ({
			filters: {
				is_transporter: 1,
			},
		}));

		frm.set_query("supplier", () => ({
			filters: {
				is_transporter: 0,
				custom_is_party: 0,
			},
		}));
	},

	onload_post_render(frm){
		setTimeout(() => {
			if (frm.doc.custom_po_created) {
				frm.remove_custom_button(__("Purchase Order"), __("Create"));
				frm.remove_custom_button(__("Quotation"), __("Create"));
			}
		}, 300);
	},

	refresh(frm) {
		setTimeout(() => {
			if (frm.doc.custom_po_created) {
				frm.remove_custom_button(__("Purchase Order"), __("Create"));
				frm.remove_custom_button(__("Quotation"), __("Create"));
			}
		}, 300);

		// Show linked PO references as indicators for quick navigation
		if (frm.doc.custom_material_purchase_order_reference_) {
			frm.add_custom_button(__("Material PO"), () => {
				frappe.set_route("Form", "Purchase Order", frm.doc.custom_material_purchase_order_reference_);
			}, __("View"));
		}

		if (frm.doc.custom_transporter_purchase_order_reference_) {
			frm.add_custom_button(__("Transport PO"), () => {
				frappe.set_route("Form", "Purchase Order", frm.doc.custom_transporter_purchase_order_reference_);
			}, __("View"));
		}
	},
});


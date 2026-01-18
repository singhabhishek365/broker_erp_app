// frappe.ui.form.on("Supplier Quotation", {
// 	custom_freight(frm) {
// 		if (!frm.doc.items) return;

// 		// ---- EXCLUSIVE → ADD FREIGHT ----
// 		if (frm.doc.custom_freight === "Exclusive") {
// 			let exists = frm.doc.items.some((i) => i.item_code === "Freight");

// 			if (!exists) {
// 				let row = frm.add_child("items");
// 				row.item_code = "Freight";
// 				row.item_name = "Freight Charges";
// 				row.uom = "Service";
// 				row.conversion_factor = 1;
// 				row.qty = 1;
// 				row.rate = frm.doc.rate || 0;

// 				frm.refresh_field("items");
// 			}
// 		}

// 		// ---- INCLUSIVE → REMOVE FREIGHT ----
// 		if (frm.doc.custom_freight === "Inclusive") {
// 			frm.doc.items = frm.doc.items.filter((i) => i.item_code !== "Freight");
// 			frm.refresh_field("items");
// 		}
// 	},
// });

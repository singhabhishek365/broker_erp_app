frappe.ui.form.on("Supplier Quotation", {
	onload(frm) {
		frm.set_query("custom_party_name_", () => ({
			filters: { custom_is_party: 1 },
		}));
	},

	custom_freight_per_unit(frm) {
		calculate_charges(frm);
	},

	custom_lobour_per_unit_(frm) {
		calculate_charges(frm);
	},
});

frappe.ui.form.on("Supplier Quotation Item", {
	qty(frm) {
		calculate_charges(frm);
	},
	items_remove(frm) {
		calculate_charges(frm);
	},
});

function calculate_charges(frm) {
	frm.trigger("calculate_totals");

	let weight = frm.doc.total_qty || 0;
	let freight_unit = frm.doc.custom_freight_per_unit || 0;
	let labour_unit = frm.doc.custom_lobour_per_unit_ || 0;

	frm.set_value("custom_total_freight_cost", freight_unit * weight);
	frm.set_value("custom_labour_total_cost_", labour_unit * weight);
}

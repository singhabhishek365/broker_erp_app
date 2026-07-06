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

	incoterm(frm) {
		if (!frm.doc.incoterm) {
			return;
		}
		frappe.db.get_value(
			"Incoterm",
			frm.doc.incoterm,
			"custom_transporter_to_be_captured_from_master"
		).then((r) => {
			if (r.message.custom_transporter_to_be_captured_from_master) {
				frm.set_value('custom_freight', 'Exclusive');
			} else {
				frm.set_value('custom_freight', 'Inclusive');
			}
		});
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

		render_po_links(frm);
	},
});

function render_po_links(frm) {
    const material_po = frm.doc.custom_material_purchase_order_reference_;
    const transporter_po = frm.doc.custom_transporter_purchase_order_reference_;

    if (!material_po && !transporter_po) {
        frm.set_df_property("custom_po_links_html", "options", "");
        return;
    }

    const make_card = (label, po_name, icon, color) => {
        if (!po_name) {
            return `
                <div class="po-link-card po-link-card--empty">
                    <div class="po-link-icon" style="background:#f0f1f3;color:#8d99a6;">
                        <i class="${icon}"></i>
                    </div>
                    <div class="po-link-body">
                        <div class="po-link-label">${label}</div>
                        <div class="po-link-value po-link-value--empty">Not yet created</div>
                    </div>
                </div>`;
        }
        const url = frappe.utils.get_form_link("Purchase Order", po_name);
        return `
            <a href="${url}" class="po-link-card">
                <div class="po-link-icon" style="background:${color}1a;color:${color};">
                    <i class="${icon}"></i>
                </div>
                <div class="po-link-body">
                    <div class="po-link-label">${label}</div>
                    <div class="po-link-value">${po_name}</div>
                </div>
                <div class="po-link-arrow">
                    <i class="fa fa-arrow-right"></i>
                </div>
            </a>`;
    };

    const html = `
        <style>
            .po-link-wrapper {
                display: flex;
                gap: 12px;
                flex-wrap: wrap;
                margin: 6px 0 14px;
            }
            .po-link-card {
                display: flex;
                align-items: center;
                gap: 12px;
                flex: 1 1 260px;
                min-width: 240px;
                padding: 14px 16px;
                border: 1px solid var(--border-color, #d1d8dd);
                border-radius: 8px;
                background: var(--card-bg, #fff);
                text-decoration: none !important;
                transition: box-shadow .15s ease, transform .15s ease;
            }
            .po-link-card:not(.po-link-card--empty):hover {
                box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                transform: translateY(-1px);
            }
            .po-link-card--empty {
                cursor: default;
                border-style: dashed;
            }
            .po-link-icon {
                width: 38px;
                height: 38px;
                min-width: 38px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 16px;
            }
            .po-link-body {
                flex: 1;
                min-width: 0;
            }
            .po-link-label {
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: .04em;
                color: var(--text-muted, #8d99a6);
                margin-bottom: 2px;
            }
            .po-link-value {
                font-size: 14px;
                font-weight: 600;
                color: var(--text-color, #1a1a1a);
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            .po-link-value--empty {
                font-weight: 400;
                font-style: italic;
                color: var(--text-muted, #a8b1b9);
            }
            .po-link-arrow {
                color: var(--text-muted, #c2c9cf);
                font-size: 12px;
            }
            .po-link-card:hover .po-link-arrow {
                color: var(--text-color, #1a1a1a);
            }
        </style>
        <div class="po-link-wrapper">
            ${make_card("Material Purchase Order", material_po, "fa fa-cube", "#2e7d32")}
            ${make_card("Transporter Purchase Order", transporter_po, "fa fa-truck", "#1565c0")}
        </div>
    `;

    frm.set_df_property("custom_po_links_html", "options", html);
}


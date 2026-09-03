frappe.ui.form.on("Supplier Quotation", {
    refresh(frm) {
        update_supplier_label(frm);

        if (!frappe.user.has_role("System Manager")) {
            toggle_item_code_editable(frm);
        }

        if (
            frm.is_new() &&
            frm.doc.items &&
            frm.doc.items.length > 0 &&
            frm.doc.items[0].material_request
        ) {
            frappe.db.get_doc(
                "Material Request",
                frm.doc.items[0].material_request
            ).then(mr => {
                frm.set_value("department", mr.custom_department);
                frm.set_value("cost_center", mr.custom_cost_center);
                frm.set_value("branch", mr.custom_branch);
            });
        }

        setTimeout(() => {
            // Remove standard Create menu items.
            frm.remove_custom_button(__("Material Request"), __("Get Items From"));
            frm.remove_custom_button(__("Request for Quotation"), __("Get Items From"));
            frm.remove_custom_button(__("Link to Material Requests"), __("Tools"));
        }, 400);

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

        (frm.doc.custom_transporters || []).forEach((row) => {
            if (!row.transporter_po_reference) return;
            frm.add_custom_button(row.transporter_po_reference, () => {
                frappe.set_route("Form", "Purchase Order", row.transporter_po_reference);
            }, __("Transport PO"));
        });

        render_po_links(frm);
    },
    custom_is_broker_quotation(frm) {
        update_supplier_label(frm);
    },
    cost_center(frm) {
        $.each(frm.doc.items, function (i, d) {
            frappe.model.set_value(d.doctype, d.name, "cost_center", frm.doc.cost_center);
        });
    },
    branch(frm) {
        $.each(frm.doc.items, function (i, d) {
            frappe.model.set_value(d.doctype, d.name, "branch", frm.doc.branch);
        });
    },
    department(frm) {
        $.each(frm.doc.items, function (i, d) {
            frappe.model.set_value(d.doctype, d.name, "department", frm.doc.department);
        });
    },
    validate(frm) {
        frm.trigger("custom_rate_per_unit");
    },
    custom_rate_per_unit(frm) {
        if (frm.doc.custom_rate_per_unit && frm.doc.custom_rate_per_unit <= 0) {
            frappe.msgprint({
                title: __("Invalid Rate"),
                message: __("Rate Per Unit must be greater than 0."),
                indicator: "red",
            });
            frm.set_value("custom_rate_per_unit", "");
        }
    },
    onload(frm) {
        update_supplier_label(frm);
        frm.set_query("custom_party_name_", () => ({
            filters: { custom_is_party: 1 },
        }));

        frm.set_query("transporter", "custom_transporters", () => ({
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
    onload_post_render(frm) {
        setTimeout(() => {
            if (frm.doc.custom_po_created) {
                frm.remove_custom_button(__("Purchase Order"), __("Create"));
                frm.remove_custom_button(__("Quotation"), __("Create"));
            }
        }, 300);
    }
});

frappe.ui.form.on("Supplier Quotation Item", {
    items_add(frm) {
        if (!frappe.user.has_role("System Manager")) toggle_item_code_editable(frm);
    },
    items_remove(frm) {
        if (!frappe.user.has_role("System Manager")) toggle_item_code_editable(frm);
    },
});

function toggle_item_code_editable(frm) {
    const items_grid = frm.fields_dict["items"] && frm.fields_dict["items"].grid;
    if (!items_grid) return;

    const has_source_doc_field = (frm.doc.items || []).some(
        (row) => row.material_request || row.request_for_quotation
    );

    if (has_source_doc_field) {
        items_grid.update_docfield_property("item_code", "read_only", 1);
        items_grid.cannot_add_rows = true;
        items_grid.df.cannot_add_rows = 1;
        items_grid.cannot_delete_rows = false;
        items_grid.df.cannot_delete_rows = 0;
    } else {
        items_grid.update_docfield_property("item_code", "read_only", 0);
        items_grid.cannot_add_rows = false;
        items_grid.df.cannot_add_rows = 0;
        items_grid.cannot_delete_rows = false;
        items_grid.df.cannot_delete_rows = 0;
    }

    items_grid.refresh();
    items_grid.grid_rows.forEach((row) => {
        row.refresh_field("item_code");
    });
}

function render_po_links(frm) {
    // Fetch the Material PO live from Purchase Order instead of trusting the
    // cached custom_material_purchase_order_reference_ field on this SQ.
    frappe.db.get_list("Purchase Order", {
        filters: [
            ["Purchase Order Item", "supplier_quotation", "=", frm.doc.name],
            ["Purchase Order", "custom_purchase_type", "=", "Material"],
            ["Purchase Order", "docstatus", "!=", 2],
        ],
        fields: ["name"],
        limit: 1,
    }).then((rows) => {
        const material_po = rows && rows.length ? rows[0].name : null;

        // if (!material_po) {
        //     render_po_link_cards(frm, null, []);
        //     return;
        // }

        // Fetch Transporter PO(s) live via their custom_material_po link,
        // instead of trusting custom_transporters / the legacy reference
        // field on this SQ (Transporter POs can be created directly against
        // the Material PO, bypassing this SQ entirely).
        // frappe.db.get_list("Purchase Order", {
        //     filters: {
        //         custom_material_po: material_po,
        //         custom_is_transporter_po: 1,
        //         docstatus: ["!=", 2],
        //     },
        //     fields: ["name", "supplier"],
        //     order_by: "creation asc",
        //     limit: 100,
        // }).then((transporter_pos) => {
        //     render_po_link_cards(frm, material_po, transporter_pos);
        // });
    });
}

function render_po_link_cards(frm, material_po, transporter_pos) {
    if (!material_po && !transporter_pos.length) {
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
                gap: 8px;
                flex-wrap: wrap;
                margin: 4px 0 10px;
            }
            .po-link-card {
                display: flex;
                align-items: center;
                gap: 8px;
                flex: 1 1 200px;
                min-width: 180px;
                padding: 8px 10px;
                border: 1px solid var(--border-color, #d1d8dd);
                border-radius: 6px;
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
                width: 26px;
                height: 26px;
                min-width: 26px;
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 12px;
            }
            .po-link-body {
                flex: 1;
                min-width: 0;
            }
            .po-link-label {
                font-size: 10px;
                text-transform: uppercase;
                letter-spacing: .03em;
                color: var(--text-muted, #8d99a6);
                margin-bottom: 1px;
            }
            .po-link-value {
                font-size: 12.5px;
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
                font-size: 11px;
            }
            .po-link-card:hover .po-link-arrow {
                color: var(--text-color, #1a1a1a);
            }
        </style>
        <div class="po-link-wrapper">
            ${make_card("Material Purchase Order", material_po, "fa fa-cube", "#2e7d32")}
            ${
                transporter_pos.length
                    ? transporter_pos.map((po) => make_card(
                        `Transporter PO (${po.supplier})`,
                        po.name,
                        "fa fa-truck",
                        "#1565c0"
                    )).join("")
                    : make_card("Transporter Purchase Order", null, "fa fa-truck", "#1565c0")
            }
        </div>
    `;

    frm.set_df_property("custom_po_links_html", "options", html);
}

function update_supplier_label(frm) {
    frm.set_df_property(
        "supplier",
        "label",
        frm.doc.custom_is_broker_quotation
            ? __("Party Name")
            : __("Supplier")
    );

    frm.refresh_field("supplier");
}
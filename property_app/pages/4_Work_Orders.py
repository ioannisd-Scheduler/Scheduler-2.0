import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.database import init_db
from core import queries as q
from datetime import date
import pandas as pd

st.set_page_config(page_title="Work Orders", page_icon="🔧", layout="wide")
init_db()

st.title("🔧 Work Orders")

PRIORITIES = ["emergency", "high", "medium", "low"]
CATEGORIES = ["plumbing", "electrical", "hvac", "painting", "general", "appliance", "structural", "landscaping", "other"]
STATUSES = ["open", "in_progress", "pending_parts", "completed", "cancelled"]

PRIORITY_BADGE = {
    "emergency": "🔴 Emergency",
    "high": "🟠 High",
    "medium": "🟡 Medium",
    "low": "🟢 Low",
}
STATUS_LABEL = {
    "open": "Open",
    "in_progress": "In Progress",
    "pending_parts": "Pending Parts",
    "completed": "Completed",
    "cancelled": "Cancelled",
}

# ── Filters (sidebar) ─────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")
    props = q.get_properties()
    prop_opts = {"All Properties": None} | {p["name"]: p["id"] for p in props}
    filter_prop = st.selectbox("Property", list(prop_opts.keys()))
    filter_status = st.multiselect("Status", STATUSES, default=["open","in_progress","pending_parts"])
    filter_priority = st.multiselect("Priority", PRIORITIES)

# ── Create Work Order ─────────────────────────────────────────────────────────
with st.expander("➕ New Work Order", expanded=False):
    units = q.get_units()
    unit_map = {"— None —": None} | {f"{u['property_name']} · Unit {u['unit_number']}": u["id"] for u in units}
    tenants = q.get_tenants(status="active")
    tenant_map = {"— None —": None} | {f"{t['first_name']} {t['last_name']}": t["id"] for t in tenants}
    subs = q.get_subcontractors(active_only=True)
    sub_map = {"— Unassigned —": None} | {s["company_name"]: s["id"] for s in subs}

    with st.form("new_wo"):
        title = st.text_input("Title *", placeholder="e.g. Leaking kitchen faucet")
        description = st.text_area("Description", height=80)

        c1, c2, c3 = st.columns(3)
        priority = c1.selectbox("Priority", PRIORITIES, index=2)
        category = c2.selectbox("Category", CATEGORIES, index=4)
        status = c3.selectbox("Status", STATUSES, index=0)

        c4, c5 = st.columns(2)
        prop_sel = c4.selectbox("Property", ["— None —"] + [p["name"] for p in props])
        unit_sel = c5.selectbox("Unit", list(unit_map.keys()))

        c6, c7 = st.columns(2)
        tenant_sel = c6.selectbox("Reported By (Tenant)", list(tenant_map.keys()))
        sub_sel = c7.selectbox("Assigned To (Subcontractor)", list(sub_map.keys()))

        dc1, dc2, dc3, dc4 = st.columns(4)
        reported_date = dc1.date_input("Reported Date", value=date.today())
        scheduled_date = dc2.date_input("Scheduled Date", value=None)
        est_cost = dc3.number_input("Est. Cost ($)", min_value=0.0, step=25.0, value=0.0)
        act_cost = dc4.number_input("Actual Cost ($)", min_value=0.0, step=25.0, value=0.0)

        notes = st.text_area("Notes", height=60)

        if st.form_submit_button("Create Work Order", type="primary"):
            if not title:
                st.error("Title is required.")
            else:
                pid = next((p["id"] for p in props if p["name"] == prop_sel), None)
                q.create_work_order(
                    pid, unit_map.get(unit_sel), tenant_map.get(tenant_sel),
                    sub_map.get(sub_sel), title, description, priority, category,
                    status, str(reported_date),
                    str(scheduled_date) if scheduled_date else None,
                    None, est_cost or None, act_cost or None, notes
                )
                st.success("Work order created.")
                st.rerun()

# ── Import from spreadsheet ───────────────────────────────────────────────────
with st.expander("📥 Import from Spreadsheet"):
    st.markdown("Upload your existing maintenance/service-call spreadsheet (.xlsx or .csv).")
    uploaded = st.file_uploader("Choose file", type=["xlsx", "xls", "csv"])
    if uploaded:
        try:
            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)
            st.dataframe(df.head(5), use_container_width=True)
            st.markdown("**Map your columns to work order fields:**")
            cols = ["— skip —"] + list(df.columns)

            mc1, mc2, mc3 = st.columns(3)
            col_title = mc1.selectbox("Title column *", cols)
            col_desc = mc2.selectbox("Description column", cols)
            col_priority = mc3.selectbox("Priority column", cols)
            mc4, mc5, mc6 = st.columns(3)
            col_status = mc4.selectbox("Status column", cols)
            col_date = mc5.selectbox("Reported Date column", cols)
            col_cost = mc6.selectbox("Cost column", cols)

            if st.button("Import Rows", type="primary"):
                if col_title == "— skip —":
                    st.error("Title column is required.")
                else:
                    count = 0
                    for _, row in df.iterrows():
                        title_val = str(row[col_title]) if col_title != "— skip —" else "Imported"
                        desc_val = str(row[col_desc]) if col_desc != "— skip —" else ""
                        pri_val = str(row[col_priority]).lower() if col_priority != "— skip —" else "medium"
                        pri_val = pri_val if pri_val in PRIORITIES else "medium"
                        status_val = str(row[col_status]).lower().replace(" ", "_") if col_status != "— skip —" else "open"
                        status_val = status_val if status_val in STATUSES else "open"
                        date_val = str(row[col_date]) if col_date != "— skip —" else str(date.today())
                        try:
                            date_val = str(pd.to_datetime(date_val).date())
                        except Exception:
                            date_val = str(date.today())
                        cost_val = None
                        if col_cost != "— skip —":
                            try:
                                cost_val = float(str(row[col_cost]).replace("$","").replace(",",""))
                            except Exception:
                                cost_val = None
                        q.create_work_order(None, None, None, None, title_val, desc_val,
                                            pri_val, "general", status_val, date_val,
                                            None, None, cost_val, None, "Imported from spreadsheet")
                        count += 1
                    st.success(f"Imported {count} work orders.")
                    st.rerun()
        except Exception as e:
            st.error(f"Could not read file: {e}")

st.divider()

# ── Work order list ───────────────────────────────────────────────────────────
sel_pid = prop_opts.get(filter_prop)
work_orders = q.get_work_orders(property_id=sel_pid)

if filter_status:
    work_orders = [w for w in work_orders if w["status"] in filter_status]
if filter_priority:
    work_orders = [w for w in work_orders if w["priority"] in filter_priority]

# Summary counts
counts = {s: sum(1 for w in work_orders if w["status"] == s) for s in STATUSES}
sc = st.columns(len(STATUSES))
for i, s in enumerate(STATUSES):
    sc[i].metric(STATUS_LABEL[s], counts[s])

st.divider()

if not work_orders:
    st.info("No work orders match the current filters.")
else:
    units = q.get_units()
    unit_map_full = {"— None —": None} | {f"{u['property_name']} · Unit {u['unit_number']}": u["id"] for u in units}
    tenants = q.get_tenants()
    tenant_map_full = {"— None —": None} | {f"{t['first_name']} {t['last_name']}": t["id"] for t in tenants}
    subs = q.get_subcontractors()
    sub_map_full = {"— Unassigned —": None} | {s["company_name"]: s["id"] for s in subs}

    for wo in work_orders:
        loc = wo.get("property_name") or "No property"
        if wo.get("unit_number"):
            loc += f" · Unit {wo['unit_number']}"
        badge = PRIORITY_BADGE.get(wo["priority"], wo["priority"])
        status_lbl = STATUS_LABEL.get(wo["status"], wo["status"])
        label = f"{badge} | **{wo['title']}** · {loc} · {status_lbl}"

        with st.expander(label):
            with st.form(f"edit_wo_{wo['id']}"):
                title_e = st.text_input("Title", value=wo["title"])
                desc_e = st.text_area("Description", value=wo.get("description",""), height=80)

                c1, c2, c3 = st.columns(3)
                pri_e = c1.selectbox("Priority", PRIORITIES, index=PRIORITIES.index(wo["priority"]))
                cat_e = c2.selectbox("Category", CATEGORIES, index=CATEGORIES.index(wo.get("category","general")))
                stat_e = c3.selectbox("Status", STATUSES, index=STATUSES.index(wo["status"]))

                c4, c5 = st.columns(2)
                prop_names = ["— None —"] + [p["name"] for p in props]
                cur_prop = wo.get("property_name") or "— None —"
                prop_idx = prop_names.index(cur_prop) if cur_prop in prop_names else 0
                prop_e = c4.selectbox("Property", prop_names, index=prop_idx)

                cur_unit_label = next((k for k, v in unit_map_full.items() if v == wo.get("unit_id")), "— None —")
                unit_choices = list(unit_map_full.keys())
                unit_e = c5.selectbox("Unit", unit_choices, index=unit_choices.index(cur_unit_label))

                c6, c7 = st.columns(2)
                cur_t_label = next((k for k, v in tenant_map_full.items() if v == wo.get("tenant_id")), "— None —")
                t_choices = list(tenant_map_full.keys())
                tenant_e = c6.selectbox("Tenant", t_choices, index=t_choices.index(cur_t_label))

                cur_s_label = next((k for k, v in sub_map_full.items() if v == wo.get("subcontractor_id")), "— Unassigned —")
                s_choices = list(sub_map_full.keys())
                sub_e = c7.selectbox("Subcontractor", s_choices, index=s_choices.index(cur_s_label))

                dc1, dc2, dc3, dc4 = st.columns(4)
                rep_e = dc1.date_input("Reported", value=date.fromisoformat(wo["reported_date"]))
                sched_val = date.fromisoformat(wo["scheduled_date"]) if wo.get("scheduled_date") else None
                sched_e = dc2.date_input("Scheduled", value=sched_val)
                comp_val = date.fromisoformat(wo["completed_date"]) if wo.get("completed_date") else None
                comp_e = dc3.date_input("Completed", value=comp_val)
                est_e = dc4.number_input("Est. Cost ($)", min_value=0.0, value=float(wo.get("estimated_cost") or 0), step=25.0)
                act_e = st.number_input("Actual Cost ($)", min_value=0.0, value=float(wo.get("actual_cost") or 0), step=25.0)

                notes_e = st.text_area("Notes", value=wo.get("notes",""), height=60)

                bc1, bc2, _ = st.columns([1,1,4])
                if bc1.form_submit_button("Update", type="primary"):
                    new_pid = next((p["id"] for p in props if p["name"] == prop_e), None)
                    q.update_work_order(
                        wo["id"], new_pid, unit_map_full.get(unit_e),
                        tenant_map_full.get(tenant_e), sub_map_full.get(sub_e),
                        title_e, desc_e, pri_e, cat_e, stat_e, str(rep_e),
                        str(sched_e) if sched_e else None,
                        str(comp_e) if comp_e else None,
                        est_e or None, act_e or None, notes_e
                    )
                    st.success("Updated.")
                    st.rerun()
                if bc2.form_submit_button("Delete", type="secondary"):
                    q.delete_work_order(wo["id"])
                    st.warning("Work order deleted.")
                    st.rerun()

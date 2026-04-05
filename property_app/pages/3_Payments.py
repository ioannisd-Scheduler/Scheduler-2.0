import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.database import init_db
from core import queries as q
from datetime import date, timedelta

st.set_page_config(page_title="Payments", page_icon="💰", layout="wide")
init_db()

st.title("💰 Rent & Payments")

METHODS = ["", "Check", "ACH/Bank Transfer", "Zelle", "Venmo", "Cash", "Money Order", "Credit Card", "Other"]

# ── Log Payment ───────────────────────────────────────────────────────────────
with st.expander("➕ Log Payment", expanded=False):
    tenants = q.get_tenants(status="active")
    tenant_map = {f"{t['first_name']} {t['last_name']} — {t.get('property_name','?')} Unit {t.get('unit_number','?')}": t
                  for t in tenants}

    with st.form("new_payment"):
        tenant_sel = st.selectbox("Tenant *", ["— Select Tenant —"] + list(tenant_map.keys()))

        # Auto-fill rent amount
        selected_tenant = tenant_map.get(tenant_sel)
        default_rent = float(selected_tenant["monthly_rent"]) if selected_tenant else 0.0
        default_unit = selected_tenant["unit_id"] if selected_tenant else None
        default_tid = selected_tenant["id"] if selected_tenant else None

        c1, c2 = st.columns(2)
        amount = c1.number_input("Amount ($) *", min_value=0.0, value=default_rent, step=50.0)
        late_fee = c2.number_input("Late Fee ($)", min_value=0.0, value=0.0, step=5.0)

        c3, c4 = st.columns(2)
        due_date = c3.date_input("Due Date *", value=date.today().replace(day=1))
        paid_date = c4.date_input("Paid Date (leave blank if unpaid)", value=None)

        c5, c6 = st.columns(2)
        method = c5.selectbox("Payment Method", METHODS)
        ref_num = c6.text_input("Reference / Check #")

        notes = st.text_area("Notes", height=60)

        if st.form_submit_button("Save Payment", type="primary"):
            if tenant_sel == "— Select Tenant —":
                st.error("Select a tenant.")
            else:
                q.create_payment(default_tid, default_unit, amount, str(due_date),
                                 str(paid_date) if paid_date else None,
                                 method or None, ref_num or None, late_fee, notes)
                st.success("Payment logged.")
                st.rerun()

st.divider()

# ── Bulk-charge monthly rent ──────────────────────────────────────────────────
with st.expander("📅 Bulk Charge Monthly Rent"):
    st.markdown("Create a payment record (unpaid) for every active tenant for a given month.")
    charge_month = st.date_input("Rent Due Date", value=date.today().replace(day=1), key="bulk_due")
    if st.button("Create Rent Charges", type="primary"):
        active = q.get_tenants(status="active")
        count = 0
        for t in active:
            if t.get("monthly_rent") and t["monthly_rent"] > 0:
                q.create_payment(t["id"], t.get("unit_id"), t["monthly_rent"],
                                 str(charge_month), None, None, None, 0, "Bulk monthly charge")
                count += 1
        st.success(f"Created {count} payment records.")
        st.rerun()

st.divider()

# ── Filters ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")
    filter_paid = st.radio("Payment Status", ["All", "Paid", "Unpaid / Overdue"])
    props = q.get_properties()
    prop_map = {"All Properties": None} | {p["name"]: p["id"] for p in props}
    filter_prop = st.selectbox("Property", list(prop_map.keys()))

# ── Payment list ──────────────────────────────────────────────────────────────
all_payments = q.get_payments()
today = date.today()

# Apply filters
if filter_paid == "Paid":
    all_payments = [p for p in all_payments if p.get("paid_date")]
elif filter_paid == "Unpaid / Overdue":
    all_payments = [p for p in all_payments if not p.get("paid_date")]

if prop_map.get(filter_prop):
    pid = prop_map[filter_prop]
    units_in_prop = {u["id"] for u in q.get_units(property_id=pid)}
    all_payments = [p for p in all_payments if p.get("unit_id") in units_in_prop]

# Summary metrics
total_collected = sum(p["amount"] + p["late_fee"] for p in all_payments if p.get("paid_date"))
total_outstanding = sum(p["amount"] + p["late_fee"] for p in all_payments if not p.get("paid_date"))
overdue_count = sum(1 for p in all_payments if not p.get("paid_date") and p["due_date"] < str(today))

mc1, mc2, mc3 = st.columns(3)
mc1.metric("Collected (filtered)", f"${total_collected:,.0f}")
mc2.metric("Outstanding (filtered)", f"${total_outstanding:,.0f}")
mc3.metric("Overdue (filtered)", overdue_count)

st.divider()

if not all_payments:
    st.info("No payments match the current filters.")
else:
    for pmt in all_payments:
        tenant_name = f"{pmt.get('first_name','')} {pmt.get('last_name','')}".strip() or "Unknown"
        unit_label = f"{pmt.get('property_name','?')} · Unit {pmt.get('unit_number','?')}"
        is_paid = bool(pmt.get("paid_date"))
        is_overdue = not is_paid and pmt["due_date"] < str(today)
        status_icon = "✅" if is_paid else ("🔴" if is_overdue else "🕐")
        total_due = pmt["amount"] + (pmt["late_fee"] or 0)
        label = f"{status_icon} **{tenant_name}** · {unit_label} — ${total_due:,.2f} due {pmt['due_date']}"
        if is_paid:
            label += f" — paid {pmt['paid_date']}"

        with st.expander(label):
            with st.form(f"edit_pmt_{pmt['id']}"):
                tenants_all = q.get_tenants()
                tenant_map_all = {"— None —": (None, None)}
                for t in tenants_all:
                    k = f"{t['first_name']} {t['last_name']} — {t.get('property_name','?')} Unit {t.get('unit_number','?')}"
                    tenant_map_all[k] = (t["id"], t.get("unit_id"))
                t_choices = list(tenant_map_all.keys())
                cur_t_label = next((k for k, v in tenant_map_all.items() if v[0] == pmt.get("tenant_id")), "— None —")
                t_sel = st.selectbox("Tenant", t_choices, index=t_choices.index(cur_t_label))

                c1, c2 = st.columns(2)
                amt_e = c1.number_input("Amount ($)", min_value=0.0, value=float(pmt["amount"]), step=50.0)
                fee_e = c2.number_input("Late Fee ($)", min_value=0.0, value=float(pmt.get("late_fee") or 0), step=5.0)

                c3, c4 = st.columns(2)
                due_e = c3.date_input("Due Date", value=date.fromisoformat(pmt["due_date"]))
                paid_val = date.fromisoformat(pmt["paid_date"]) if pmt.get("paid_date") else None
                paid_e = c4.date_input("Paid Date", value=paid_val)

                c5, c6 = st.columns(2)
                method_idx = METHODS.index(pmt.get("payment_method") or "") if (pmt.get("payment_method") or "") in METHODS else 0
                method_e = c5.selectbox("Method", METHODS, index=method_idx)
                ref_e = c6.text_input("Reference #", value=pmt.get("reference_number") or "")
                notes_e = st.text_area("Notes", value=pmt.get("notes") or "", height=60)

                bc1, bc2, _ = st.columns([1,1,4])
                if bc1.form_submit_button("Update", type="primary"):
                    tid_e, uid_e = tenant_map_all.get(t_sel, (None, None))
                    q.update_payment(pmt["id"], tid_e, uid_e, amt_e, str(due_e),
                                     str(paid_e) if paid_e else None,
                                     method_e or None, ref_e or None, fee_e, notes_e)
                    st.success("Updated.")
                    st.rerun()
                if bc2.form_submit_button("Delete", type="secondary"):
                    q.delete_payment(pmt["id"])
                    st.warning("Payment deleted.")
                    st.rerun()

import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.database import init_db
from core import queries as q
from datetime import date

st.set_page_config(page_title="Tenants", page_icon="👤", layout="wide")
init_db()

st.title("👤 Tenants")

STATUS_OPTS = ["active", "past", "applicant"]

# ── Filters ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")
    filter_status = st.multiselect("Status", STATUS_OPTS, default=["active"])
    filter_search = st.text_input("Search name / email")

# ── Add Tenant ────────────────────────────────────────────────────────────────
with st.expander("➕ Add New Tenant", expanded=False):
    units = q.get_units()
    unit_map = {f"{u['property_name']} · Unit {u['unit_number']}": u["id"] for u in units}

    with st.form("new_tenant"):
        c1, c2 = st.columns(2)
        first = c1.text_input("First Name *")
        last = c2.text_input("Last Name *")
        c3, c4 = st.columns(2)
        email = c3.text_input("Email")
        phone = c4.text_input("Phone")

        unit_choices = ["— No Unit —"] + list(unit_map.keys())
        unit_sel = st.selectbox("Assigned Unit", unit_choices)

        c5, c6 = st.columns(2)
        ec_name = c5.text_input("Emergency Contact Name")
        ec_phone = c6.text_input("Emergency Contact Phone")

        st.markdown("**Lease & Financials**")
        lc1, lc2, lc3, lc4 = st.columns(4)
        lease_start = lc1.date_input("Lease Start", value=None)
        lease_end = lc2.date_input("Lease End", value=None)
        monthly_rent = lc3.number_input("Monthly Rent ($)", min_value=0.0, step=50.0)
        deposit = lc4.number_input("Security Deposit ($)", min_value=0.0, step=50.0)

        status = st.selectbox("Status", STATUS_OPTS)
        notes = st.text_area("Notes", height=80)

        if st.form_submit_button("Save Tenant", type="primary"):
            if not first or not last:
                st.error("First and last name are required.")
            else:
                uid = unit_map.get(unit_sel) if unit_sel != "— No Unit —" else None
                q.create_tenant(uid, first, last, email, phone, ec_name, ec_phone,
                                str(lease_start) if lease_start else None,
                                str(lease_end) if lease_end else None,
                                monthly_rent, deposit, status, notes)
                # Sync unit status to occupied
                if uid and status == "active":
                    unit = q.get_unit(uid)
                    if unit and unit["status"] == "vacant":
                        q.update_unit(uid, unit["property_id"], unit["unit_number"],
                                      unit["bedrooms"], unit["bathrooms"], unit["sq_ft"],
                                      unit["monthly_rent"], "occupied", unit.get("notes",""))
                st.success(f"Tenant {first} {last} created.")
                st.rerun()

# ── Tenant list ───────────────────────────────────────────────────────────────
tenants = q.get_tenants()

if filter_status:
    tenants = [t for t in tenants if t["status"] in filter_status]

if filter_search:
    s = filter_search.lower()
    tenants = [t for t in tenants if s in (t["first_name"] + " " + t["last_name"]).lower()
               or s in (t.get("email") or "").lower()]

if not tenants:
    st.info("No tenants match the current filters.")
else:
    STATUS_BADGE = {"active": "🟢 Active", "past": "⚪ Past", "applicant": "🔵 Applicant"}

    for tenant in tenants:
        name = f"{tenant['first_name']} {tenant['last_name']}"
        loc = tenant.get("property_name") or "No unit assigned"
        if tenant.get("unit_number"):
            loc += f" · Unit {tenant['unit_number']}"
        badge = STATUS_BADGE.get(tenant["status"], tenant["status"])

        # Lease expiry warning
        lease_warning = ""
        if tenant.get("lease_end") and tenant["status"] == "active":
            try:
                end = date.fromisoformat(tenant["lease_end"])
                days_left = (end - date.today()).days
                if days_left < 0:
                    lease_warning = " ⚠️ Lease expired"
                elif days_left <= 30:
                    lease_warning = f" ⚠️ Expires in {days_left}d"
                elif days_left <= 60:
                    lease_warning = f" ℹ️ Expires in {days_left}d"
            except ValueError:
                pass

        with st.expander(f"{badge} — **{name}** · {loc}{lease_warning}"):
            units_all = q.get_units()
            unit_map = {f"{u['property_name']} · Unit {u['unit_number']}": u["id"] for u in units_all}
            unit_choices = ["— No Unit —"] + list(unit_map.keys())

            with st.form(f"edit_tenant_{tenant['id']}"):
                c1, c2 = st.columns(2)
                first_e = c1.text_input("First Name", value=tenant["first_name"])
                last_e = c2.text_input("Last Name", value=tenant["last_name"])
                c3, c4 = st.columns(2)
                email_e = c3.text_input("Email", value=tenant.get("email",""))
                phone_e = c4.text_input("Phone", value=tenant.get("phone",""))

                cur_unit_label = next((k for k, v in unit_map.items() if v == tenant.get("unit_id")), "— No Unit —")
                unit_sel_e = st.selectbox("Unit", unit_choices, index=unit_choices.index(cur_unit_label))

                c5, c6 = st.columns(2)
                ec_name_e = c5.text_input("Emergency Contact Name", value=tenant.get("emergency_contact_name",""))
                ec_phone_e = c6.text_input("Emergency Contact Phone", value=tenant.get("emergency_contact_phone",""))

                st.markdown("**Lease & Financials**")
                lc1, lc2, lc3, lc4 = st.columns(4)
                ls_val = date.fromisoformat(tenant["lease_start"]) if tenant.get("lease_start") else None
                le_val = date.fromisoformat(tenant["lease_end"]) if tenant.get("lease_end") else None
                ls_e = lc1.date_input("Lease Start", value=ls_val)
                le_e = lc2.date_input("Lease End", value=le_val)
                rent_e = lc3.number_input("Monthly Rent ($)", min_value=0.0, value=float(tenant.get("monthly_rent") or 0), step=50.0)
                dep_e = lc4.number_input("Deposit ($)", min_value=0.0, value=float(tenant.get("security_deposit") or 0), step=50.0)

                status_e = st.selectbox("Status", STATUS_OPTS, index=STATUS_OPTS.index(tenant["status"]))
                notes_e = st.text_area("Notes", value=tenant.get("notes",""), height=80)

                bc1, bc2, _ = st.columns([1,1,4])
                if bc1.form_submit_button("Update", type="primary"):
                    uid_e = unit_map.get(unit_sel_e) if unit_sel_e != "— No Unit —" else None
                    q.update_tenant(tenant["id"], uid_e, first_e, last_e, email_e, phone_e,
                                    ec_name_e, ec_phone_e,
                                    str(ls_e) if ls_e else None,
                                    str(le_e) if le_e else None,
                                    rent_e, dep_e, status_e, notes_e)
                    st.success("Updated.")
                    st.rerun()
                if bc2.form_submit_button("Delete", type="secondary"):
                    q.delete_tenant(tenant["id"])
                    st.warning("Tenant deleted.")
                    st.rerun()

            # Payments summary
            payments = q.get_payments(tenant_id=tenant["id"])
            if payments:
                st.markdown("**Recent Payments:**")
                rows = [{
                    "Due Date": p["due_date"],
                    "Paid Date": p.get("paid_date") or "UNPAID",
                    "Amount": f"${p['amount']:,.2f}",
                    "Late Fee": f"${p['late_fee']:,.2f}" if p["late_fee"] else "—",
                    "Method": p.get("payment_method") or "—",
                } for p in payments[:5]]
                st.dataframe(rows, use_container_width=True, hide_index=True)

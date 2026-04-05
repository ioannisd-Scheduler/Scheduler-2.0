import streamlit as st
from core.database import init_db
from core import queries as q

st.set_page_config(
    page_title="Property Manager",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Bootstrap DB on first run
init_db()

st.title("🏠 Property Management Dashboard")
st.caption("Overview of your portfolio")

stats = q.get_dashboard_stats()

# ── KPI row 1 ─────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

with col1:
    occupancy_pct = (stats["occupied"] / stats["total_units"] * 100) if stats["total_units"] else 0
    st.metric("Occupancy", f"{stats['occupied']} / {stats['total_units']} units", f"{occupancy_pct:.0f}%")

with col2:
    st.metric("Vacant Units", stats["vacant"],
              delta=None if stats["vacant"] == 0 else f"{stats['vacant']} needs attention",
              delta_color="inverse")

with col3:
    st.metric("Active Tenants", stats["active_tenants"])

with col4:
    st.metric("Monthly Rent Expected", f"${stats['monthly_expected']:,.0f}")

st.divider()

# ── KPI row 2 ─────────────────────────────────────────────────────────────────
col5, col6, col7, col8 = st.columns(4)

with col5:
    color = "normal" if stats["emergency_wo"] == 0 else "inverse"
    st.metric("Open Work Orders", stats["open_work_orders"],
              delta=f"{stats['emergency_wo']} emergency" if stats["emergency_wo"] else None,
              delta_color=color)

with col6:
    st.metric("Overdue Rent", f"${stats['unpaid_rent']:,.0f}",
              delta="Unpaid past due date" if stats["unpaid_rent"] > 0 else "All current",
              delta_color="inverse" if stats["unpaid_rent"] > 0 else "normal")

with col7:
    st.metric("Leases Expiring (60 days)", stats["expiring_leases"],
              delta="Action needed" if stats["expiring_leases"] > 0 else None,
              delta_color="inverse" if stats["expiring_leases"] > 0 else "normal")

with col8:
    st.metric("Contractor Insurance Expiring (30 days)", stats["insurance_expiring"],
              delta="Review needed" if stats["insurance_expiring"] > 0 else None,
              delta_color="inverse" if stats["insurance_expiring"] > 0 else "normal")

st.divider()

# ── Active work orders ────────────────────────────────────────────────────────
st.subheader("Active Work Orders")

PRIORITY_BADGE = {
    "emergency": "🔴 Emergency",
    "high": "🟠 High",
    "medium": "🟡 Medium",
    "low": "🟢 Low",
}
STATUS_BADGE = {
    "open": "Open",
    "in_progress": "In Progress",
    "pending_parts": "Pending Parts",
    "completed": "Completed",
    "cancelled": "Cancelled",
}

recent_wos = q.get_recent_work_orders(limit=10)

if recent_wos:
    for wo in recent_wos:
        loc = wo.get("property_name") or "—"
        if wo.get("unit_number"):
            loc += f" · Unit {wo['unit_number']}"
        badge = PRIORITY_BADGE.get(wo["priority"], wo["priority"])
        status = STATUS_BADGE.get(wo["status"], wo["status"])
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            c1.markdown(f"**{wo['title']}**  \n{loc}")
            c2.markdown(badge)
            c3.markdown(status)
            c4.markdown(f"#{wo['id']}")
else:
    st.info("No open work orders. Great job!")

# ── Overdue payments ──────────────────────────────────────────────────────────
overdue = q.get_overdue_payments()
if overdue:
    st.divider()
    st.subheader("Overdue Payments")
    rows = []
    for p in overdue:
        name = f"{p.get('first_name','')} {p.get('last_name','')}".strip() or "—"
        rows.append({
            "Tenant": name,
            "Unit": p.get("unit_number") or "—",
            "Property": p.get("property_name") or "—",
            "Amount": f"${(p['amount'] + p['late_fee']):,.2f}",
            "Due Date": p["due_date"],
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

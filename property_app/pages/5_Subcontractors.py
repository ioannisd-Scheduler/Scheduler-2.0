import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.database import init_db
from core import queries as q
from datetime import date

st.set_page_config(page_title="Subcontractors", page_icon="👷", layout="wide")
init_db()

st.title("👷 Subcontractors / Vendors")

TRADES = ["General Contractor", "Plumber", "Electrician", "HVAC", "Painter", "Landscaper",
          "Roofer", "Carpenter", "Cleaner", "Handyman", "Pest Control", "Locksmith", "Other"]

# ── Add Subcontractor ─────────────────────────────────────────────────────────
with st.expander("➕ Add Subcontractor", expanded=False):
    with st.form("new_sub"):
        c1, c2 = st.columns(2)
        company = c1.text_input("Company Name *")
        contact = c2.text_input("Contact Name")

        c3, c4, c5 = st.columns(3)
        trade = c3.selectbox("Trade", TRADES)
        phone = c4.text_input("Phone")
        email = c5.text_input("Email")

        address = st.text_input("Address")

        c6, c7, c8, c9 = st.columns(4)
        license_num = c6.text_input("License #")
        ins_expiry = c7.date_input("Insurance Expires", value=None)
        rating = c8.selectbox("Rating", [None, 1, 2, 3, 4, 5], format_func=lambda x: "— No rating —" if x is None else "⭐" * x)
        is_active = c9.checkbox("Active", value=True)

        notes = st.text_area("Notes", height=60)

        if st.form_submit_button("Save", type="primary"):
            if not company:
                st.error("Company name is required.")
            else:
                q.create_subcontractor(company, contact, trade, phone, email, address,
                                       license_num, str(ins_expiry) if ins_expiry else None,
                                       rating, 1 if is_active else 0, notes)
                st.success(f"{company} added.")
                st.rerun()

# ── Filters ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")
    show_inactive = st.checkbox("Show inactive", value=False)
    filter_trade = st.selectbox("Trade", ["All"] + TRADES)
    filter_search = st.text_input("Search name")

# ── List ──────────────────────────────────────────────────────────────────────
subs = q.get_subcontractors(active_only=not show_inactive)
today = date.today()

if filter_trade != "All":
    subs = [s for s in subs if s.get("trade") == filter_trade]

if filter_search:
    fs = filter_search.lower()
    subs = [s for s in subs if fs in s["company_name"].lower() or fs in (s.get("contact_name") or "").lower()]

if not subs:
    st.info("No subcontractors found.")
else:
    for sub in subs:
        # Insurance expiry warning
        ins_warn = ""
        if sub.get("insurance_expiry"):
            try:
                exp = date.fromisoformat(sub["insurance_expiry"])
                days = (exp - today).days
                if days < 0:
                    ins_warn = " 🔴 Insurance EXPIRED"
                elif days <= 30:
                    ins_warn = f" ⚠️ Insurance expires in {days}d"
            except ValueError:
                pass

        stars = "⭐" * int(sub["rating"]) if sub.get("rating") else ""
        active_badge = "🟢" if sub["is_active"] else "⚫"
        label = f"{active_badge} **{sub['company_name']}** · {sub.get('trade','—')} {stars}{ins_warn}"

        with st.expander(label):
            with st.form(f"edit_sub_{sub['id']}"):
                c1, c2 = st.columns(2)
                company_e = c1.text_input("Company Name", value=sub["company_name"])
                contact_e = c2.text_input("Contact Name", value=sub.get("contact_name",""))

                c3, c4, c5 = st.columns(3)
                trade_idx = TRADES.index(sub["trade"]) if sub.get("trade") in TRADES else len(TRADES)-1
                trade_e = c3.selectbox("Trade", TRADES, index=trade_idx)
                phone_e = c4.text_input("Phone", value=sub.get("phone",""))
                email_e = c5.text_input("Email", value=sub.get("email",""))

                addr_e = st.text_input("Address", value=sub.get("address",""))

                c6, c7, c8, c9 = st.columns(4)
                lic_e = c6.text_input("License #", value=sub.get("license_number",""))
                ins_val = date.fromisoformat(sub["insurance_expiry"]) if sub.get("insurance_expiry") else None
                ins_e = c7.date_input("Insurance Expires", value=ins_val)
                rating_opts = [None, 1, 2, 3, 4, 5]
                cur_rating = sub.get("rating")
                rat_idx = rating_opts.index(cur_rating) if cur_rating in rating_opts else 0
                rat_e = c8.selectbox("Rating", rating_opts, index=rat_idx, format_func=lambda x: "— No rating —" if x is None else "⭐" * x)
                active_e = c9.checkbox("Active", value=bool(sub["is_active"]))

                notes_e = st.text_area("Notes", value=sub.get("notes",""), height=60)

                bc1, bc2, _ = st.columns([1,1,4])
                if bc1.form_submit_button("Update", type="primary"):
                    q.update_subcontractor(sub["id"], company_e, contact_e, trade_e, phone_e,
                                           email_e, addr_e, lic_e,
                                           str(ins_e) if ins_e else None,
                                           rat_e, 1 if active_e else 0, notes_e)
                    st.success("Updated.")
                    st.rerun()
                if bc2.form_submit_button("Delete", type="secondary"):
                    q.delete_subcontractor(sub["id"])
                    st.warning("Subcontractor deleted.")
                    st.rerun()

            # Recent work orders for this sub
            wo_list = q.get_work_orders()
            sub_wos = [w for w in wo_list if w.get("subcontractor_id") == sub["id"]]
            if sub_wos:
                st.markdown(f"**Work orders assigned ({len(sub_wos)}):**")
                rows = [{
                    "Title": w["title"],
                    "Property": w.get("property_name","—"),
                    "Priority": w["priority"].capitalize(),
                    "Status": w["status"].replace("_"," ").capitalize(),
                    "Date": w["reported_date"],
                } for w in sub_wos[:5]]
                st.dataframe(rows, use_container_width=True, hide_index=True)

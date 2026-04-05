import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.database import init_db
from core import queries as q

st.set_page_config(page_title="Properties", page_icon="🏢", layout="wide")
init_db()

st.title("🏢 Properties & Units")

tab_props, tab_units = st.tabs(["Properties", "Units"])

# ── Properties tab ────────────────────────────────────────────────────────────
with tab_props:
    with st.expander("➕ Add New Property", expanded=False):
        with st.form("new_property"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Property Name *")
            ptype = c2.selectbox("Type", ["residential", "commercial", "multi-family", "condo", "other"])
            address = st.text_input("Address")
            cc1, cc2, cc3 = st.columns([3, 2, 1])
            city = cc1.text_input("City")
            state = cc2.text_input("State")
            zip_ = cc3.text_input("ZIP")
            notes = st.text_area("Notes", height=80)
            if st.form_submit_button("Save Property", type="primary"):
                if not name:
                    st.error("Property name is required.")
                else:
                    q.create_property(name, address, city, state, zip_, ptype, notes)
                    st.success(f"Property '{name}' created.")
                    st.rerun()

    properties = q.get_properties()
    if not properties:
        st.info("No properties yet. Add one above.")
    else:
        for prop in properties:
            units = q.get_units(property_id=prop["id"])
            occupied = sum(1 for u in units if u["status"] == "occupied")
            with st.expander(f"**{prop['name']}** — {prop.get('address_line1','')} {prop.get('city','')}  ·  {occupied}/{len(units)} occupied"):
                with st.form(f"edit_prop_{prop['id']}"):
                    c1, c2 = st.columns(2)
                    name_e = c1.text_input("Name", value=prop["name"])
                    ptype_e = c2.selectbox("Type", ["residential","commercial","multi-family","condo","other"],
                                           index=["residential","commercial","multi-family","condo","other"].index(prop.get("property_type","residential")))
                    addr_e = st.text_input("Address", value=prop.get("address_line1",""))
                    cc1, cc2, cc3 = st.columns([3,2,1])
                    city_e = cc1.text_input("City", value=prop.get("city",""))
                    state_e = cc2.text_input("State", value=prop.get("state",""))
                    zip_e = cc3.text_input("ZIP", value=prop.get("zip",""))
                    notes_e = st.text_area("Notes", value=prop.get("notes",""), height=80)
                    bc1, bc2, _ = st.columns([1,1,4])
                    if bc1.form_submit_button("Update", type="primary"):
                        q.update_property(prop["id"], name_e, addr_e, city_e, state_e, zip_e, ptype_e, notes_e)
                        st.success("Updated.")
                        st.rerun()
                    if bc2.form_submit_button("Delete", type="secondary"):
                        q.delete_property(prop["id"])
                        st.warning(f"'{prop['name']}' deleted.")
                        st.rerun()

                # Units mini-table
                if units:
                    st.markdown("**Units:**")
                    rows = [{
                        "Unit": u["unit_number"],
                        "Bed/Bath": f"{u['bedrooms']}bd/{u['bathrooms']}ba",
                        "Sq Ft": u["sq_ft"] or "—",
                        "Rent": f"${u['monthly_rent']:,.0f}",
                        "Status": u["status"].capitalize(),
                    } for u in units]
                    st.dataframe(rows, use_container_width=True, hide_index=True)

# ── Units tab ─────────────────────────────────────────────────────────────────
with tab_units:
    properties = q.get_properties()
    prop_map = {p["name"]: p["id"] for p in properties}

    with st.expander("➕ Add New Unit", expanded=False):
        if not properties:
            st.warning("Add a property first.")
        else:
            with st.form("new_unit"):
                prop_sel = st.selectbox("Property *", list(prop_map.keys()))
                c1, c2 = st.columns(2)
                unit_num = c1.text_input("Unit Number *", placeholder="e.g. 1A, 201")
                status = c2.selectbox("Status", ["vacant", "occupied", "maintenance"])
                c3, c4, c5, c6 = st.columns(4)
                beds = c3.number_input("Bedrooms", min_value=0, max_value=20, value=1)
                baths = c4.number_input("Bathrooms", min_value=0.0, max_value=20.0, value=1.0, step=0.5)
                sqft = c5.number_input("Sq Ft", min_value=0, value=0)
                rent = c6.number_input("Monthly Rent ($)", min_value=0.0, value=0.0, step=50.0)
                notes = st.text_area("Notes", height=60)
                if st.form_submit_button("Save Unit", type="primary"):
                    if not unit_num:
                        st.error("Unit number is required.")
                    else:
                        q.create_unit(prop_map[prop_sel], unit_num, beds, baths,
                                      sqft or None, rent, status, notes)
                        st.success(f"Unit {unit_num} created.")
                        st.rerun()

    # List all units grouped by property
    all_units = q.get_units()
    if not all_units:
        st.info("No units yet.")
    else:
        STATUS_COLOR = {"occupied": "🟢", "vacant": "🔵", "maintenance": "🔴"}
        for unit in all_units:
            badge = STATUS_COLOR.get(unit["status"], "⚪")
            label = f"{badge} **{unit['property_name']}** · Unit {unit['unit_number']} — {unit['bedrooms']}bd/{unit['bathrooms']}ba — ${unit['monthly_rent']:,.0f}/mo — {unit['status'].capitalize()}"
            with st.expander(label):
                with st.form(f"edit_unit_{unit['id']}"):
                    pc1, pc2 = st.columns(2)
                    prop_names = [p["name"] for p in properties]
                    cur_prop_idx = next((i for i, p in enumerate(properties) if p["id"] == unit["property_id"]), 0)
                    prop_e = pc1.selectbox("Property", prop_names, index=cur_prop_idx)
                    unit_num_e = pc2.text_input("Unit Number", value=unit["unit_number"])
                    c1, c2, c3, c4 = st.columns(4)
                    beds_e = c1.number_input("Bedrooms", min_value=0, max_value=20, value=int(unit["bedrooms"] or 1))
                    baths_e = c2.number_input("Bathrooms", min_value=0.0, value=float(unit["bathrooms"] or 1.0), step=0.5)
                    sqft_e = c3.number_input("Sq Ft", min_value=0, value=int(unit["sq_ft"] or 0))
                    rent_e = c4.number_input("Rent ($)", min_value=0.0, value=float(unit["monthly_rent"] or 0), step=50.0)
                    status_opts = ["vacant","occupied","maintenance"]
                    status_e = st.selectbox("Status", status_opts, index=status_opts.index(unit["status"]))
                    notes_e = st.text_area("Notes", value=unit.get("notes",""), height=60)
                    bc1, bc2, _ = st.columns([1,1,4])
                    if bc1.form_submit_button("Update", type="primary"):
                        new_pid = next(p["id"] for p in properties if p["name"] == prop_e)
                        q.update_unit(unit["id"], new_pid, unit_num_e, beds_e, baths_e,
                                      sqft_e or None, rent_e, status_e, notes_e)
                        st.success("Updated.")
                        st.rerun()
                    if bc2.form_submit_button("Delete", type="secondary"):
                        q.delete_unit(unit["id"])
                        st.warning("Unit deleted.")
                        st.rerun()

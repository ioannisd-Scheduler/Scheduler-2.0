import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.database import init_db
from core import queries as q
from utils.export import expenses_to_csv, expenses_to_iif
from datetime import date
from pathlib import Path

st.set_page_config(page_title="Expenses", page_icon="🧾", layout="wide")
init_db()

RECEIPTS_DIR = Path(__file__).parent.parent / "data" / "receipts"
RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)

st.title("🧾 Expenses")

CATEGORIES = ["repair", "maintenance", "insurance", "tax", "utility", "management_fee", "capital_improvement", "other"]
METHODS = ["", "Check", "Credit Card", "ACH/Bank Transfer", "Cash", "Zelle", "Venmo", "Other"]

# ── Add Expense ───────────────────────────────────────────────────────────────
with st.expander("➕ Add Expense", expanded=False):
    props = q.get_properties()
    prop_map = {"— None —": None} | {p["name"]: p["id"] for p in props}
    work_orders = q.get_work_orders()
    wo_map = {"— None —": None} | {f"#{w['id']} {w['title']}": w["id"] for w in work_orders}

    with st.form("new_expense"):
        c1, c2 = st.columns(2)
        prop_sel = c1.selectbox("Property", list(prop_map.keys()))
        wo_sel = c2.selectbox("Linked Work Order", list(wo_map.keys()))

        c3, c4 = st.columns(2)
        vendor = c3.text_input("Vendor Name")
        category = c4.selectbox("Category", CATEGORIES)

        description = st.text_input("Description *")

        c5, c6, c7 = st.columns(3)
        amount = c5.number_input("Amount ($) *", min_value=0.0, step=5.0)
        exp_date = c6.date_input("Expense Date *", value=date.today())
        method = c7.selectbox("Payment Method", METHODS)

        c8, c9 = st.columns(2)
        qb_class = c8.text_input("QuickBooks Class", placeholder="e.g. Rental Property A")
        is_reimb = c9.checkbox("Reimbursable")

        receipt_file = st.file_uploader("Receipt (image or PDF)", type=["jpg","jpeg","png","pdf","webp"])
        notes = st.text_area("Notes", height=60)

        if st.form_submit_button("Save Expense", type="primary"):
            if not description or amount <= 0:
                st.error("Description and amount are required.")
            else:
                receipt_path = None
                receipt_name = None
                # Receipt saved after creating the expense (need ID)
                eid = q.create_expense(
                    prop_map.get(prop_sel), wo_map.get(wo_sel),
                    vendor, category, description, amount, str(exp_date),
                    method or None, None, None, qb_class, 1 if is_reimb else 0, notes
                )
                if receipt_file:
                    receipt_name = receipt_file.name
                    receipt_path = RECEIPTS_DIR / f"{eid}_{receipt_name}"
                    receipt_path.write_bytes(receipt_file.read())
                    q.update_expense(eid, prop_map.get(prop_sel), wo_map.get(wo_sel),
                                     vendor, category, description, amount, str(exp_date),
                                     method or None, str(receipt_path), receipt_name,
                                     qb_class, 1 if is_reimb else 0, notes)
                st.success("Expense saved.")
                st.rerun()

st.divider()

# ── Filters ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")
    filter_prop_name = st.selectbox("Property", ["All"] + [p["name"] for p in props])
    filter_cat = st.multiselect("Category", CATEGORIES)
    col_d1, col_d2 = st.columns(2)
    date_from = col_d1.date_input("From", value=None)
    date_to = col_d2.date_input("To", value=None)

filter_pid = next((p["id"] for p in props if p["name"] == filter_prop_name), None) if filter_prop_name != "All" else None
expenses = q.get_expenses(
    property_id=filter_pid,
    date_from=str(date_from) if date_from else None,
    date_to=str(date_to) if date_to else None,
)
if filter_cat:
    expenses = [e for e in expenses if e["category"] in filter_cat]

# ── Export ────────────────────────────────────────────────────────────────────
if expenses:
    st.subheader("Export")
    ec1, ec2 = st.columns(2)
    csv_data = expenses_to_csv(expenses)
    ec1.download_button("⬇️ Download CSV", csv_data, "expenses.csv", "text/csv")
    iif_data = expenses_to_iif(expenses)
    ec2.download_button("⬇️ Download QuickBooks IIF", iif_data, "expenses.iif", "text/plain")
    st.divider()

# ── Summary ───────────────────────────────────────────────────────────────────
total = sum(e["amount"] for e in expenses)
mc1, mc2 = st.columns(2)
mc1.metric("Total (filtered)", f"${total:,.2f}")
mc2.metric("Entries", len(expenses))

st.divider()

# ── Expense list ──────────────────────────────────────────────────────────────
if not expenses:
    st.info("No expenses match the current filters.")
else:
    for exp in expenses:
        prop_name = exp.get("property_name") or "No property"
        label = f"**{exp['expense_date']}** · {prop_name} · {exp['category'].replace('_',' ').title()} · ${exp['amount']:,.2f} — {exp['description'][:60]}"

        with st.expander(label):
            # Show receipt if available
            if exp.get("receipt_file_path") and Path(exp["receipt_file_path"]).exists():
                rpath = Path(exp["receipt_file_path"])
                if rpath.suffix.lower() in [".jpg",".jpeg",".png",".webp"]:
                    try:
                        from PIL import Image
                        img = Image.open(rpath)
                        img.thumbnail((400, 400))
                        st.image(img, caption=exp.get("receipt_original_name","Receipt"))
                    except Exception:
                        pass
                st.download_button("⬇️ Download Receipt", rpath.read_bytes(),
                                   exp.get("receipt_original_name","receipt"),
                                   key=f"dl_receipt_{exp['id']}")

            with st.form(f"edit_exp_{exp['id']}"):
                c1, c2 = st.columns(2)
                prop_e = c1.selectbox("Property", list(prop_map.keys()),
                                      index=list(prop_map.keys()).index(
                                          next((p["name"] for p in props if p["id"] == exp.get("property_id")), "— None —")))
                wo_e = c2.selectbox("Work Order", list(wo_map.keys()),
                                    index=list(wo_map.keys()).index(
                                        next((k for k, v in wo_map.items() if v == exp.get("work_order_id")), "— None —")))

                c3, c4 = st.columns(2)
                vendor_e = c3.text_input("Vendor", value=exp.get("vendor_name",""))
                cat_e = c4.selectbox("Category", CATEGORIES, index=CATEGORIES.index(exp.get("category","repair")))

                desc_e = st.text_input("Description", value=exp["description"])

                c5, c6, c7 = st.columns(3)
                amt_e = c5.number_input("Amount ($)", min_value=0.0, value=float(exp["amount"]), step=5.0)
                date_e = c6.date_input("Date", value=date.fromisoformat(exp["expense_date"]))
                meth_idx = METHODS.index(exp.get("payment_method") or "") if (exp.get("payment_method") or "") in METHODS else 0
                meth_e = c7.selectbox("Method", METHODS, index=meth_idx)

                c8, c9 = st.columns(2)
                qb_e = c8.text_input("QB Class", value=exp.get("quickbooks_class",""))
                reimb_e = c9.checkbox("Reimbursable", value=bool(exp.get("is_reimbursable")))

                new_receipt = st.file_uploader("Replace Receipt", type=["jpg","jpeg","png","pdf","webp"], key=f"repl_{exp['id']}")
                notes_e = st.text_area("Notes", value=exp.get("notes",""), height=60)

                bc1, bc2, _ = st.columns([1,1,4])
                if bc1.form_submit_button("Update", type="primary"):
                    rp = exp.get("receipt_file_path")
                    rn = exp.get("receipt_original_name")
                    if new_receipt:
                        rn = new_receipt.name
                        rp = str(RECEIPTS_DIR / f"{exp['id']}_{rn}")
                        Path(rp).write_bytes(new_receipt.read())
                    q.update_expense(exp["id"], prop_map.get(prop_e), wo_map.get(wo_e),
                                     vendor_e, cat_e, desc_e, amt_e, str(date_e),
                                     meth_e or None, rp, rn, qb_e,
                                     1 if reimb_e else 0, notes_e)
                    st.success("Updated.")
                    st.rerun()
                if bc2.form_submit_button("Delete", type="secondary"):
                    # Remove receipt file if exists
                    if exp.get("receipt_file_path"):
                        try:
                            Path(exp["receipt_file_path"]).unlink(missing_ok=True)
                        except Exception:
                            pass
                    q.delete_expense(exp["id"])
                    st.warning("Expense deleted.")
                    st.rerun()

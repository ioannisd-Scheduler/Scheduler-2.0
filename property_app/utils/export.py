"""Export utilities: CSV and QuickBooks IIF formats."""
from __future__ import annotations
import csv
import io
from datetime import date


def expenses_to_csv(expenses: list[dict]) -> bytes:
    """Return expense records as UTF-8 CSV bytes."""
    fieldnames = [
        "Date", "Property", "Vendor", "Category", "Description",
        "Amount", "Payment Method", "QB Class", "Reimbursable",
        "Work Order", "Notes",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for e in expenses:
        writer.writerow({
            "Date": e.get("expense_date",""),
            "Property": e.get("property_name",""),
            "Vendor": e.get("vendor_name",""),
            "Category": (e.get("category","")).replace("_"," ").title(),
            "Description": e.get("description",""),
            "Amount": f"{e.get('amount',0):.2f}",
            "Payment Method": e.get("payment_method",""),
            "QB Class": e.get("quickbooks_class",""),
            "Reimbursable": "Yes" if e.get("is_reimbursable") else "No",
            "Work Order": e.get("work_order_title",""),
            "Notes": e.get("notes",""),
        })
    return buf.getvalue().encode("utf-8")


def expenses_to_iif(expenses: list[dict]) -> bytes:
    """
    Return QuickBooks Desktop IIF (Intuit Interchange Format).
    Creates general journal entries.
    """
    lines: list[str] = []

    # IIF headers
    lines.append("!TRNS\tTRNSTYPE\tDATE\tACCNT\tNAME\tCLASS\tAMOUNT\tMEMO")
    lines.append("!SPL\tTRNSTYPE\tDATE\tACCNT\tNAME\tCLASS\tAMOUNT\tMEMO")
    lines.append("!ENDTRNS")

    for e in expenses:
        raw_date = e.get("expense_date","")
        # Convert YYYY-MM-DD → MM/DD/YYYY for QuickBooks
        try:
            d = date.fromisoformat(raw_date)
            qb_date = d.strftime("%m/%d/%Y")
        except (ValueError, TypeError):
            qb_date = raw_date

        amount = float(e.get("amount") or 0)
        vendor = e.get("vendor_name") or ""
        memo = e.get("description","")
        qb_class = e.get("quickbooks_class","") or ""
        category = (e.get("category","") or "").replace("_"," ").title()

        # Debit: expense account
        lines.append(
            f"TRNS\tGENJRNL\t{qb_date}\t{category}\t{vendor}\t{qb_class}\t{-amount:.2f}\t{memo}"
        )
        # Credit: bank / accounts payable
        lines.append(
            f"SPL\tGENJRNL\t{qb_date}\tAccounts Payable\t{vendor}\t{qb_class}\t{amount:.2f}\t{memo}"
        )
        lines.append("ENDTRNS")

    return "\n".join(lines).encode("utf-8")

"""All database queries. No raw SQL in page files."""
from __future__ import annotations
from typing import Any
from .database import get_connection


# ── Helpers ──────────────────────────────────────────────────────────────────

def _rows(sql: str, params: tuple = ()) -> list[dict]:
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def _one(sql: str, params: tuple = ()) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None


def _run(sql: str, params: tuple = ()) -> int:
    """Execute and return lastrowid."""
    with get_connection() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid


# ── Properties ────────────────────────────────────────────────────────────────

def get_properties() -> list[dict]:
    return _rows("SELECT * FROM properties ORDER BY name")


def get_property(pid: int) -> dict | None:
    return _one("SELECT * FROM properties WHERE id = ?", (pid,))


def create_property(name, address_line1, city, state, zip_, property_type, notes) -> int:
    return _run(
        "INSERT INTO properties (name, address_line1, city, state, zip, property_type, notes) VALUES (?,?,?,?,?,?,?)",
        (name, address_line1, city, state, zip_, property_type, notes),
    )


def update_property(pid, name, address_line1, city, state, zip_, property_type, notes):
    _run(
        "UPDATE properties SET name=?, address_line1=?, city=?, state=?, zip=?, property_type=?, notes=? WHERE id=?",
        (name, address_line1, city, state, zip_, property_type, notes, pid),
    )


def delete_property(pid: int):
    _run("DELETE FROM properties WHERE id = ?", (pid,))


# ── Units ─────────────────────────────────────────────────────────────────────

def get_units(property_id: int | None = None) -> list[dict]:
    if property_id:
        return _rows(
            "SELECT u.*, p.name as property_name FROM units u JOIN properties p ON p.id=u.property_id WHERE u.property_id=? ORDER BY u.unit_number",
            (property_id,),
        )
    return _rows("SELECT u.*, p.name as property_name FROM units u JOIN properties p ON p.id=u.property_id ORDER BY p.name, u.unit_number")


def get_unit(uid: int) -> dict | None:
    return _one("SELECT u.*, p.name as property_name FROM units u JOIN properties p ON p.id=u.property_id WHERE u.id=?", (uid,))


def create_unit(property_id, unit_number, bedrooms, bathrooms, sq_ft, monthly_rent, status, notes) -> int:
    return _run(
        "INSERT INTO units (property_id, unit_number, bedrooms, bathrooms, sq_ft, monthly_rent, status, notes) VALUES (?,?,?,?,?,?,?,?)",
        (property_id, unit_number, bedrooms, bathrooms, sq_ft, monthly_rent, status, notes),
    )


def update_unit(uid, property_id, unit_number, bedrooms, bathrooms, sq_ft, monthly_rent, status, notes):
    _run(
        "UPDATE units SET property_id=?, unit_number=?, bedrooms=?, bathrooms=?, sq_ft=?, monthly_rent=?, status=?, notes=? WHERE id=?",
        (property_id, unit_number, bedrooms, bathrooms, sq_ft, monthly_rent, status, notes, uid),
    )


def delete_unit(uid: int):
    _run("DELETE FROM units WHERE id = ?", (uid,))


# ── Tenants ───────────────────────────────────────────────────────────────────

def get_tenants(status: str | None = None) -> list[dict]:
    base = """
        SELECT t.*, u.unit_number, p.name as property_name
        FROM tenants t
        LEFT JOIN units u ON u.id = t.unit_id
        LEFT JOIN properties p ON p.id = u.property_id
    """
    if status:
        return _rows(base + " WHERE t.status=? ORDER BY t.last_name, t.first_name", (status,))
    return _rows(base + " ORDER BY t.last_name, t.first_name")


def get_tenant(tid: int) -> dict | None:
    return _one("""
        SELECT t.*, u.unit_number, p.name as property_name, p.id as property_id
        FROM tenants t
        LEFT JOIN units u ON u.id = t.unit_id
        LEFT JOIN properties p ON p.id = u.property_id
        WHERE t.id = ?
    """, (tid,))


def create_tenant(unit_id, first_name, last_name, email, phone, emergency_contact_name,
                  emergency_contact_phone, lease_start, lease_end, monthly_rent,
                  security_deposit, status, notes) -> int:
    return _run(
        """INSERT INTO tenants (unit_id, first_name, last_name, email, phone,
           emergency_contact_name, emergency_contact_phone, lease_start, lease_end,
           monthly_rent, security_deposit, status, notes)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (unit_id, first_name, last_name, email, phone, emergency_contact_name,
         emergency_contact_phone, lease_start, lease_end, monthly_rent,
         security_deposit, status, notes),
    )


def update_tenant(tid, unit_id, first_name, last_name, email, phone,
                  emergency_contact_name, emergency_contact_phone, lease_start,
                  lease_end, monthly_rent, security_deposit, status, notes):
    _run(
        """UPDATE tenants SET unit_id=?, first_name=?, last_name=?, email=?, phone=?,
           emergency_contact_name=?, emergency_contact_phone=?, lease_start=?,
           lease_end=?, monthly_rent=?, security_deposit=?, status=?, notes=?
           WHERE id=?""",
        (unit_id, first_name, last_name, email, phone, emergency_contact_name,
         emergency_contact_phone, lease_start, lease_end, monthly_rent,
         security_deposit, status, notes, tid),
    )


def delete_tenant(tid: int):
    _run("DELETE FROM tenants WHERE id = ?", (tid,))


# ── Payments ──────────────────────────────────────────────────────────────────

def get_payments(tenant_id: int | None = None, unit_id: int | None = None) -> list[dict]:
    sql = """
        SELECT pay.*, t.first_name, t.last_name, u.unit_number, p.name as property_name
        FROM payments pay
        LEFT JOIN tenants t ON t.id = pay.tenant_id
        LEFT JOIN units u ON u.id = pay.unit_id
        LEFT JOIN properties p ON p.id = u.property_id
    """
    if tenant_id:
        return _rows(sql + " WHERE pay.tenant_id=? ORDER BY pay.due_date DESC", (tenant_id,))
    if unit_id:
        return _rows(sql + " WHERE pay.unit_id=? ORDER BY pay.due_date DESC", (unit_id,))
    return _rows(sql + " ORDER BY pay.due_date DESC")


def get_overdue_payments() -> list[dict]:
    return _rows("""
        SELECT pay.*, t.first_name, t.last_name, u.unit_number, p.name as property_name
        FROM payments pay
        LEFT JOIN tenants t ON t.id = pay.tenant_id
        LEFT JOIN units u ON u.id = pay.unit_id
        LEFT JOIN properties p ON p.id = u.property_id
        WHERE pay.paid_date IS NULL AND pay.due_date < date('now')
        ORDER BY pay.due_date
    """)


def create_payment(tenant_id, unit_id, amount, due_date, paid_date, payment_method,
                   reference_number, late_fee, notes) -> int:
    return _run(
        """INSERT INTO payments (tenant_id, unit_id, amount, due_date, paid_date,
           payment_method, reference_number, late_fee, notes)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (tenant_id, unit_id, amount, due_date, paid_date or None, payment_method,
         reference_number, late_fee, notes),
    )


def update_payment(pid, tenant_id, unit_id, amount, due_date, paid_date,
                   payment_method, reference_number, late_fee, notes):
    _run(
        """UPDATE payments SET tenant_id=?, unit_id=?, amount=?, due_date=?,
           paid_date=?, payment_method=?, reference_number=?, late_fee=?, notes=?
           WHERE id=?""",
        (tenant_id, unit_id, amount, due_date, paid_date or None, payment_method,
         reference_number, late_fee, notes, pid),
    )


def delete_payment(pid: int):
    _run("DELETE FROM payments WHERE id = ?", (pid,))


# ── Work Orders ───────────────────────────────────────────────────────────────

PRIORITY_ORDER = {"emergency": 0, "high": 1, "medium": 2, "low": 3}


def get_work_orders(property_id: int | None = None, status: str | None = None,
                    priority: str | None = None) -> list[dict]:
    conditions = []
    params: list[Any] = []
    if property_id:
        conditions.append("wo.property_id = ?")
        params.append(property_id)
    if status:
        conditions.append("wo.status = ?")
        params.append(status)
    if priority:
        conditions.append("wo.priority = ?")
        params.append(priority)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return _rows(f"""
        SELECT wo.*,
               p.name as property_name,
               u.unit_number,
               t.first_name || ' ' || t.last_name as tenant_name,
               s.company_name as subcontractor_name
        FROM work_orders wo
        LEFT JOIN properties p ON p.id = wo.property_id
        LEFT JOIN units u ON u.id = wo.unit_id
        LEFT JOIN tenants t ON t.id = wo.tenant_id
        LEFT JOIN subcontractors s ON s.id = wo.subcontractor_id
        {where}
        ORDER BY
            CASE wo.priority WHEN 'emergency' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
            wo.reported_date DESC
    """, tuple(params))


def get_work_order(wid: int) -> dict | None:
    return _one("""
        SELECT wo.*,
               p.name as property_name,
               u.unit_number,
               t.first_name || ' ' || t.last_name as tenant_name,
               s.company_name as subcontractor_name
        FROM work_orders wo
        LEFT JOIN properties p ON p.id = wo.property_id
        LEFT JOIN units u ON u.id = wo.unit_id
        LEFT JOIN tenants t ON t.id = wo.tenant_id
        LEFT JOIN subcontractors s ON s.id = wo.subcontractor_id
        WHERE wo.id = ?
    """, (wid,))


def create_work_order(property_id, unit_id, tenant_id, subcontractor_id, title, description,
                      priority, category, status, reported_date, scheduled_date,
                      completed_date, estimated_cost, actual_cost, notes) -> int:
    return _run(
        """INSERT INTO work_orders (property_id, unit_id, tenant_id, subcontractor_id,
           title, description, priority, category, status, reported_date, scheduled_date,
           completed_date, estimated_cost, actual_cost, notes)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (property_id or None, unit_id or None, tenant_id or None, subcontractor_id or None,
         title, description, priority, category, status, reported_date,
         scheduled_date or None, completed_date or None,
         estimated_cost or None, actual_cost or None, notes),
    )


def update_work_order(wid, property_id, unit_id, tenant_id, subcontractor_id, title,
                      description, priority, category, status, reported_date,
                      scheduled_date, completed_date, estimated_cost, actual_cost, notes):
    _run(
        """UPDATE work_orders SET property_id=?, unit_id=?, tenant_id=?,
           subcontractor_id=?, title=?, description=?, priority=?, category=?,
           status=?, reported_date=?, scheduled_date=?, completed_date=?,
           estimated_cost=?, actual_cost=?, notes=? WHERE id=?""",
        (property_id or None, unit_id or None, tenant_id or None, subcontractor_id or None,
         title, description, priority, category, status, reported_date,
         scheduled_date or None, completed_date or None,
         estimated_cost or None, actual_cost or None, notes, wid),
    )


def delete_work_order(wid: int):
    _run("DELETE FROM work_orders WHERE id = ?", (wid,))


# ── Subcontractors ────────────────────────────────────────────────────────────

def get_subcontractors(active_only: bool = False) -> list[dict]:
    if active_only:
        return _rows("SELECT * FROM subcontractors WHERE is_active=1 ORDER BY company_name")
    return _rows("SELECT * FROM subcontractors ORDER BY company_name")


def get_subcontractor(sid: int) -> dict | None:
    return _one("SELECT * FROM subcontractors WHERE id = ?", (sid,))


def create_subcontractor(company_name, contact_name, trade, phone, email, address,
                         license_number, insurance_expiry, rating, is_active, notes) -> int:
    return _run(
        """INSERT INTO subcontractors (company_name, contact_name, trade, phone, email,
           address, license_number, insurance_expiry, rating, is_active, notes)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (company_name, contact_name, trade, phone, email, address, license_number,
         insurance_expiry or None, rating or None, is_active, notes),
    )


def update_subcontractor(sid, company_name, contact_name, trade, phone, email, address,
                         license_number, insurance_expiry, rating, is_active, notes):
    _run(
        """UPDATE subcontractors SET company_name=?, contact_name=?, trade=?, phone=?,
           email=?, address=?, license_number=?, insurance_expiry=?, rating=?,
           is_active=?, notes=? WHERE id=?""",
        (company_name, contact_name, trade, phone, email, address, license_number,
         insurance_expiry or None, rating or None, is_active, notes, sid),
    )


def delete_subcontractor(sid: int):
    _run("DELETE FROM subcontractors WHERE id = ?", (sid,))


# ── Expenses ──────────────────────────────────────────────────────────────────

def get_expenses(property_id: int | None = None, category: str | None = None,
                 date_from: str | None = None, date_to: str | None = None) -> list[dict]:
    conditions = []
    params: list[Any] = []
    if property_id:
        conditions.append("e.property_id = ?")
        params.append(property_id)
    if category:
        conditions.append("e.category = ?")
        params.append(category)
    if date_from:
        conditions.append("e.expense_date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("e.expense_date <= ?")
        params.append(date_to)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return _rows(f"""
        SELECT e.*, p.name as property_name, wo.title as work_order_title
        FROM expenses e
        LEFT JOIN properties p ON p.id = e.property_id
        LEFT JOIN work_orders wo ON wo.id = e.work_order_id
        {where}
        ORDER BY e.expense_date DESC
    """, tuple(params))


def get_expense(eid: int) -> dict | None:
    return _one("""
        SELECT e.*, p.name as property_name, wo.title as work_order_title
        FROM expenses e
        LEFT JOIN properties p ON p.id = e.property_id
        LEFT JOIN work_orders wo ON wo.id = e.work_order_id
        WHERE e.id = ?
    """, (eid,))


def create_expense(property_id, work_order_id, vendor_name, category, description,
                   amount, expense_date, payment_method, receipt_file_path,
                   receipt_original_name, quickbooks_class, is_reimbursable, notes) -> int:
    return _run(
        """INSERT INTO expenses (property_id, work_order_id, vendor_name, category,
           description, amount, expense_date, payment_method, receipt_file_path,
           receipt_original_name, quickbooks_class, is_reimbursable, notes)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (property_id or None, work_order_id or None, vendor_name, category, description,
         amount, expense_date, payment_method, receipt_file_path or None,
         receipt_original_name or None, quickbooks_class, is_reimbursable, notes),
    )


def update_expense(eid, property_id, work_order_id, vendor_name, category, description,
                   amount, expense_date, payment_method, receipt_file_path,
                   receipt_original_name, quickbooks_class, is_reimbursable, notes):
    _run(
        """UPDATE expenses SET property_id=?, work_order_id=?, vendor_name=?, category=?,
           description=?, amount=?, expense_date=?, payment_method=?,
           receipt_file_path=?, receipt_original_name=?, quickbooks_class=?,
           is_reimbursable=?, notes=? WHERE id=?""",
        (property_id or None, work_order_id or None, vendor_name, category, description,
         amount, expense_date, payment_method, receipt_file_path or None,
         receipt_original_name or None, quickbooks_class, is_reimbursable, notes, eid),
    )


def delete_expense(eid: int):
    _run("DELETE FROM expenses WHERE id = ?", (eid,))


# ── Dashboard stats ───────────────────────────────────────────────────────────

def get_dashboard_stats() -> dict:
    with get_connection() as conn:
        total_units = conn.execute("SELECT COUNT(*) FROM units").fetchone()[0]
        occupied = conn.execute("SELECT COUNT(*) FROM units WHERE status='occupied'").fetchone()[0]
        vacant = conn.execute("SELECT COUNT(*) FROM units WHERE status='vacant'").fetchone()[0]
        active_tenants = conn.execute("SELECT COUNT(*) FROM tenants WHERE status='active'").fetchone()[0]
        open_work_orders = conn.execute("SELECT COUNT(*) FROM work_orders WHERE status NOT IN ('completed','cancelled')").fetchone()[0]
        emergency_wo = conn.execute("SELECT COUNT(*) FROM work_orders WHERE priority='emergency' AND status NOT IN ('completed','cancelled')").fetchone()[0]
        unpaid_rent = conn.execute("SELECT COALESCE(SUM(amount + late_fee),0) FROM payments WHERE paid_date IS NULL AND due_date < date('now')").fetchone()[0]
        monthly_expected = conn.execute("SELECT COALESCE(SUM(monthly_rent),0) FROM units WHERE status='occupied'").fetchone()[0]
        expiring_leases = conn.execute(
            "SELECT COUNT(*) FROM tenants WHERE status='active' AND lease_end BETWEEN date('now') AND date('now','+60 days')"
        ).fetchone()[0]
        insurance_expiring = conn.execute(
            "SELECT COUNT(*) FROM subcontractors WHERE is_active=1 AND insurance_expiry BETWEEN date('now') AND date('now','+30 days')"
        ).fetchone()[0]
    return {
        "total_units": total_units,
        "occupied": occupied,
        "vacant": vacant,
        "active_tenants": active_tenants,
        "open_work_orders": open_work_orders,
        "emergency_wo": emergency_wo,
        "unpaid_rent": unpaid_rent,
        "monthly_expected": monthly_expected,
        "expiring_leases": expiring_leases,
        "insurance_expiring": insurance_expiring,
    }


def get_recent_work_orders(limit: int = 5) -> list[dict]:
    return _rows(f"""
        SELECT wo.id, wo.title, wo.priority, wo.status, wo.reported_date,
               p.name as property_name, u.unit_number
        FROM work_orders wo
        LEFT JOIN properties p ON p.id = wo.property_id
        LEFT JOIN units u ON u.id = wo.unit_id
        WHERE wo.status NOT IN ('completed','cancelled')
        ORDER BY
            CASE wo.priority WHEN 'emergency' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
            wo.created_at DESC
        LIMIT {limit}
    """)

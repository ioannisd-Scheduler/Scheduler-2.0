import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "property_mgmt.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS properties (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                address_line1 TEXT,
                city        TEXT,
                state       TEXT,
                zip         TEXT,
                property_type TEXT DEFAULT 'residential',
                notes       TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS units (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id     INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
                unit_number     TEXT NOT NULL,
                bedrooms        INTEGER DEFAULT 1,
                bathrooms       REAL DEFAULT 1.0,
                sq_ft           INTEGER,
                monthly_rent    REAL DEFAULT 0,
                status          TEXT DEFAULT 'vacant' CHECK(status IN ('occupied','vacant','maintenance')),
                notes           TEXT
            );

            CREATE TABLE IF NOT EXISTS subcontractors (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name      TEXT NOT NULL,
                contact_name      TEXT,
                trade             TEXT,
                phone             TEXT,
                email             TEXT,
                address           TEXT,
                license_number    TEXT,
                insurance_expiry  DATE,
                rating            INTEGER CHECK(rating BETWEEN 1 AND 5),
                is_active         INTEGER DEFAULT 1,
                notes             TEXT,
                created_at        DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS tenants (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                unit_id                 INTEGER REFERENCES units(id) ON DELETE SET NULL,
                first_name              TEXT NOT NULL,
                last_name               TEXT NOT NULL,
                email                   TEXT,
                phone                   TEXT,
                emergency_contact_name  TEXT,
                emergency_contact_phone TEXT,
                lease_start             DATE,
                lease_end               DATE,
                monthly_rent            REAL DEFAULT 0,
                security_deposit        REAL DEFAULT 0,
                status                  TEXT DEFAULT 'active' CHECK(status IN ('active','past','applicant')),
                portal_enabled          INTEGER DEFAULT 0,
                portal_pin_hash         TEXT,
                notes                   TEXT,
                created_at              DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS payments (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id       INTEGER REFERENCES tenants(id) ON DELETE SET NULL,
                unit_id         INTEGER REFERENCES units(id) ON DELETE SET NULL,
                amount          REAL NOT NULL,
                due_date        DATE NOT NULL,
                paid_date       DATE,
                payment_method  TEXT,
                reference_number TEXT,
                late_fee        REAL DEFAULT 0,
                notes           TEXT,
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS work_orders (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id         INTEGER REFERENCES properties(id) ON DELETE SET NULL,
                unit_id             INTEGER REFERENCES units(id) ON DELETE SET NULL,
                tenant_id           INTEGER REFERENCES tenants(id) ON DELETE SET NULL,
                subcontractor_id    INTEGER REFERENCES subcontractors(id) ON DELETE SET NULL,
                title               TEXT NOT NULL,
                description         TEXT,
                priority            TEXT DEFAULT 'medium' CHECK(priority IN ('emergency','high','medium','low')),
                category            TEXT DEFAULT 'general' CHECK(category IN ('plumbing','electrical','hvac','painting','general','appliance','structural','landscaping','other')),
                status              TEXT DEFAULT 'open' CHECK(status IN ('open','in_progress','pending_parts','completed','cancelled')),
                reported_date       DATE DEFAULT (date('now')),
                scheduled_date      DATE,
                completed_date      DATE,
                estimated_cost      REAL,
                actual_cost         REAL,
                portal_submitted    INTEGER DEFAULT 0,
                notes               TEXT,
                created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id         INTEGER REFERENCES properties(id) ON DELETE SET NULL,
                work_order_id       INTEGER REFERENCES work_orders(id) ON DELETE SET NULL,
                vendor_name         TEXT,
                category            TEXT DEFAULT 'repair' CHECK(category IN ('repair','maintenance','insurance','tax','utility','management_fee','capital_improvement','other')),
                description         TEXT NOT NULL,
                amount              REAL NOT NULL,
                expense_date        DATE NOT NULL,
                payment_method      TEXT,
                receipt_file_path   TEXT,
                receipt_original_name TEXT,
                quickbooks_class    TEXT,
                is_reimbursable     INTEGER DEFAULT 0,
                notes               TEXT,
                created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

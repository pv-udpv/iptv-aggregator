#!/usr/bin/env python3
"""
Add taxonomy and hierarchy columns to SQLite database.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("output/iptv_full.db")


def add_column_safe(cur: sqlite3.Cursor, table: str, column: str, ddl_type: str) -> None:
    """Add column if it doesn't exist."""
    try:
        cur.execute(
            "SELECT name FROM pragma_table_info(?) WHERE name = ?",
            (table, column),
        )
        row = cur.fetchone()
        if row:
            return
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")
        print(f"  ✓ Added {table}.{column}")
    except sqlite3.Error as e:
        print(f"  ⚠ {table}.{column}: {e}")


def main() -> None:
    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} not found")
        return

    print(f"📝 Migrating {DB_PATH}...\n")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Ensure channels table exists
    try:
        cur.execute("SELECT 1 FROM channels LIMIT 1")
    except sqlite3.OperationalError:
        print("ERROR: channels table not found")
        conn.close()
        return

    print("🔧 Updating channels table:")
    add_column_safe(cur, "channels", "normalized_name", "TEXT")
    add_column_safe(cur, "channels", "resolution", "TEXT")
    add_column_safe(cur, "channels", "country_code", "TEXT")
    add_column_safe(cur, "channels", "lang_code", "TEXT")
    add_column_safe(cur, "channels", "variant", "TEXT")
    add_column_safe(cur, "channels", "parent_id", "INTEGER")
    add_column_safe(cur, "channels", "root_id", "INTEGER")
    add_column_safe(cur, "channels", "is_root", "INTEGER DEFAULT 0")
    add_column_safe(cur, "channels", "is_variant", "INTEGER DEFAULT 0")

    # matched_channels (if exists)
    try:
        cur.execute("SELECT 1 FROM matched_channels LIMIT 1")
        print("\n🔧 Updating matched_channels table:")
        add_column_safe(cur, "matched_channels", "normalized_name", "TEXT")
        add_column_safe(cur, "matched_channels", "resolution", "TEXT")
        add_column_safe(cur, "matched_channels", "country_code", "TEXT")
        add_column_safe(cur, "matched_channels", "lang_code", "TEXT")
        add_column_safe(cur, "matched_channels", "variant", "TEXT")
        add_column_safe(cur, "matched_channels", "parent_id", "INTEGER")
        add_column_safe(cur, "matched_channels", "root_id", "INTEGER")
        add_column_safe(cur, "matched_channels", "is_root", "INTEGER DEFAULT 0")
        add_column_safe(cur, "matched_channels", "is_variant", "INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        print("\n⚠ matched_channels table not found (ok)")

    conn.commit()
    conn.close()

    print("\n✅ Migration complete!")


if __name__ == "__main__":
    main()

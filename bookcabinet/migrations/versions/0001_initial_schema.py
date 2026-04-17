"""initial schema

Mirrors the tables created by `bookcabinet.database.db.Database._init_database`.
Uses ``CREATE TABLE IF NOT EXISTS`` so the migration is safe against databases
that were already bootstrapped by the application before Alembic was added.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-17 00:00:00.000000

"""
from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = '0001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cells (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            row TEXT NOT NULL,
            x INTEGER NOT NULL,
            y INTEGER NOT NULL,
            status TEXT DEFAULT 'empty',
            book_rfid TEXT,
            book_title TEXT,
            reserved_for TEXT,
            needs_extraction BOOLEAN DEFAULT 0,
            updated_at TEXT
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rfid TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            author TEXT,
            isbn TEXT,
            status TEXT DEFAULT 'in_cabinet',
            cell_id INTEGER,
            reserved_by TEXT,
            issued_to TEXT,
            issued_at TEXT,
            due_date TEXT,
            FOREIGN KEY (cell_id) REFERENCES cells(id)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rfid TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            role TEXT DEFAULT 'reader',
            card_type TEXT DEFAULT 'library',
            active BOOLEAN DEFAULT 1
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            operation TEXT NOT NULL,
            cell_row TEXT,
            cell_x INTEGER,
            cell_y INTEGER,
            book_rfid TEXT,
            user_rfid TEXT,
            result TEXT DEFAULT 'OK',
            duration_ms INTEGER DEFAULT 0,
            details TEXT
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            component TEXT
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT
        )
        """
    )


def downgrade() -> None:
    # Intentionally destructive only on explicit downgrade request.
    op.execute("DROP TABLE IF EXISTS settings")
    op.execute("DROP TABLE IF EXISTS system_logs")
    op.execute("DROP TABLE IF EXISTS operations")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP TABLE IF EXISTS books")
    op.execute("DROP TABLE IF EXISTS cells")

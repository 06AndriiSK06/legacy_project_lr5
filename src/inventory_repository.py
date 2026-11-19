"""Data access layer (Repository) for inventory SQLite operations."""

import datetime
import sqlite3
from typing import Any, List, Optional, Tuple


class InventoryRepository:
    """Encapsulates all parameterized SQL queries for inventory management."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get_stock_qty(self, product_id: int) -> Optional[int]:
        """Return current quantity in stock for a given product_id."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT qty FROM stock WHERE pid = ?", (product_id,))
        row = cursor.fetchone()
        return int(row[0]) if row else None

    def get_stock_and_reserved(self, product_id: int) -> Optional[Tuple[int, int]]:
        """Return (qty, reserved) tuple for a product."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT qty, reserved FROM stock WHERE pid = ?", (product_id,))
        row = cursor.fetchone()
        return (int(row[0]), int(row[1])) if row else None

    def reserve_item(self, product_id: int, qty: int, order_id: int) -> None:
        """Atomically increase reserved count and record reservation."""
        cursor = self.conn.cursor()
        now_str = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
        cursor.execute(
            "UPDATE stock SET reserved = reserved + ? WHERE pid = ?",
            (qty, product_id),
        )
        cursor.execute(
            "INSERT INTO reservations VALUES (?, ?, ?, ?)",
            (order_id, product_id, qty, now_str),
        )
        self.conn.commit()

    def release_item(self, product_id: int, qty: int, order_id: int) -> None:
        """Release reserved quantity and remove specific order reservation."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE stock SET reserved = reserved - ? WHERE pid = ?",
            (qty, product_id),
        )
        cursor.execute(
            "DELETE FROM reservations WHERE oid = ? AND pid = ?",
            (order_id, product_id),
        )
        self.conn.commit()

    def confirm_item(self, product_id: int, qty: int, order_id: int) -> None:
        """Deduct actual stock and clear reservation after payment confirmation."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE stock SET reserved = reserved - ? WHERE pid = ?",
            (qty, product_id),
        )
        cursor.execute(
            "UPDATE stock SET qty = qty - ? WHERE pid = ?",
            (qty, product_id),
        )
        cursor.execute(
            "DELETE FROM reservations WHERE oid = ?",
            (order_id,),
        )
        self.conn.commit()

    def fetch_report_rows(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Tuple[Any, ...]]:
        """Fetch filtered inventory join rows using parameterized SQL."""
        query = (
            "SELECT p.id, p.name, p.category, s.qty, s.reserved, "
            "s.qty - s.reserved AS available "
            "FROM products p JOIN stock s ON p.id = s.pid WHERE 1=1"
        )
        params: List[Any] = []
        if category:
            query += " AND p.category = ?"
            params.append(category)
        if start_date:
            query += " AND s.updated_at >= ?"
            params.append(start_date)
        if end_date:
            query += " AND s.updated_at <= ?"
            params.append(end_date)

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def adjust_stock(self, product_id: int, new_qty: int, reason: str = "") -> None:
        """Update stock quantity and append an audit log record."""
        old_qty = self.get_stock_qty(product_id) or 0
        now_str = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE stock SET qty = ?, updated_at = ? WHERE pid = ?",
            (new_qty, now_str, product_id),
        )
        cursor.execute(
            "INSERT INTO stock_log VALUES (?, ?, ?, ?, ?)",
            (product_id, old_qty, new_qty, reason, now_str),
        )
        self.conn.commit()

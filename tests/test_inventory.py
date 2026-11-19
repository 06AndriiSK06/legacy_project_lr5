"""Integration & unit tests for inventory module using real in-memory SQLite."""

import sqlite3
import pytest

from src.inventory import (
    check_stock,
    confirm_stock,
    get_inventory_report,
    release_stock,
    reserve_stock,
    sync_with_warehouse,
    update_stock,
)
from src.inventory_config import InventoryConfig
from src.inventory_repository import InventoryRepository


@pytest.fixture
def in_memory_repo():
    """Provide a real SQLite in-memory database populated with test warehouse data."""
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, category TEXT);
        CREATE TABLE stock (pid INTEGER PRIMARY KEY, qty INTEGER, reserved INTEGER, updated_at TEXT);
        CREATE TABLE reservations (oid INTEGER, pid INTEGER, qty INTEGER, created_at TEXT);
        CREATE TABLE stock_log (pid INTEGER, old_qty INTEGER, new_qty INTEGER, reason TEXT, changed_at TEXT);

        INSERT INTO products VALUES (1, 'Laptop', 'Electronics');
        INSERT INTO products VALUES (2, 'Mouse', 'Electronics');
        INSERT INTO products VALUES (3, 'Desk', 'Furniture');

        INSERT INTO stock VALUES (1, 15, 2, '2026-10-10');
        INSERT INTO stock VALUES (2, 5, 0, '2026-10-12');
        INSERT INTO stock VALUES (3, 0, 0, '2026-10-15');
        """
    )
    conn.commit()
    yield InventoryRepository(conn)
    conn.close()


def test_check_stock(in_memory_repo):
    assert check_stock(1, 10, repo=in_memory_repo) is True
    assert check_stock(1, 20, repo=in_memory_repo) is False
    assert check_stock(999, 1, repo=in_memory_repo) is False


def test_reserve_release_and_confirm_lifecycle(in_memory_repo):
    ok, err = reserve_stock(1, 5, order_id=101, repo=in_memory_repo)
    assert ok is True and err is None
    assert in_memory_repo.get_stock_and_reserved(1) == (15, 7)

    ok_fail, err_msg = reserve_stock(1, 10, order_id=102, repo=in_memory_repo)
    assert ok_fail is False
    assert "not enough stock" in err_msg

    assert release_stock(1, 2, order_id=101, repo=in_memory_repo) is True
    assert in_memory_repo.get_stock_and_reserved(1) == (15, 5)

    assert confirm_stock(1, 5, order_id=101, repo=in_memory_repo) is True
    assert in_memory_repo.get_stock_and_reserved(1) == (10, 0)


def test_update_stock_creates_audit_log(in_memory_repo):
    assert update_stock(2, 25, reason="Restock delivery", repo=in_memory_repo) is True
    assert in_memory_repo.get_stock_qty(2) == 25
    row = in_memory_repo.conn.execute(
        "SELECT old_qty, new_qty, reason FROM stock_log WHERE pid = 2"
    ).fetchone()
    assert row == (5, 25, "Restock delivery")


def test_get_inventory_report_aggregation_and_sql_injection_protection(in_memory_repo):
    full_report = get_inventory_report(repo=in_memory_repo)
    assert full_report["total_items"] == 3
    assert full_report["total_qty"] == 20
    assert full_report["total_reserved"] == 2
    assert full_report["low_stock"] == ["Mouse"]
    assert full_report["out_of_stock"] == ["Desk"]
    assert full_report["by_category"] == {"Electronics": 20, "Furniture": 0}

    injected = get_inventory_report(category="Electronics' OR '1'='1", repo=in_memory_repo)
    assert injected["total_items"] == 0


def test_sync_with_warehouse_uses_env_config():
    empty_cfg = InventoryConfig(warehouse_api_key="")
    assert sync_with_warehouse(config=empty_cfg)["status"] == "skipped_no_credentials"

    active_cfg = InventoryConfig(warehouse_api_key="test_key_from_env")
    assert sync_with_warehouse(config=active_cfg)["status"] == "not_implemented"
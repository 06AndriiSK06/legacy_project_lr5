"""Business logic for warehouse inventory management (reengineered)."""

import datetime
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from src.inventory_config import InventoryConfig
from src.inventory_repository import InventoryRepository

logger = logging.getLogger(__name__)
DEFAULT_CONFIG = InventoryConfig()


def get_repo(conn: Optional[sqlite3.Connection] = None) -> InventoryRepository:
    """Create an InventoryRepository using injected or configured SQLite connection."""
    active_conn = conn if conn is not None else sqlite3.connect(DEFAULT_CONFIG.db_path)
    return InventoryRepository(active_conn)


def check_stock(product_id: int, qty: int, repo: Optional[InventoryRepository] = None) -> bool:
    """Check if available stock quantity covers requested qty."""
    current_qty = (repo or get_repo()).get_stock_qty(product_id)
    return current_qty is not None and current_qty >= qty


def reserve_stock(
    product_id: int, qty: int, order_id: int, repo: Optional[InventoryRepository] = None
) -> Tuple[bool, Optional[str]]:
    """Reserve stock items for an order before payment confirmation."""
    active_repo = repo or get_repo()
    stock_info = active_repo.get_stock_and_reserved(product_id)
    if not stock_info:
        return False, "product not found"
    available = stock_info[0] - stock_info[1]
    if available < qty:
        return False, f"not enough stock: have {available} need {qty}"
    active_repo.reserve_item(product_id, qty, order_id)
    return True, None


def release_stock(
    product_id: int, qty: int, order_id: int, repo: Optional[InventoryRepository] = None
) -> bool:
    """Release previously reserved items back to available stock."""
    (repo or get_repo()).release_item(product_id, qty, order_id)
    return True


def confirm_stock(
    product_id: int, qty: int, order_id: int, repo: Optional[InventoryRepository] = None
) -> bool:
    """Deduct confirmed order items from stock and log low-stock warnings."""
    active_repo = repo or get_repo()
    active_repo.confirm_item(product_id, qty, order_id)
    remaining = active_repo.get_stock_qty(product_id)
    if remaining is not None and remaining < DEFAULT_CONFIG.low_stock_threshold:
        logger.warning("LOW STOCK WARNING: product %s (remaining=%s)", product_id, remaining)
    return True


def _aggregate_inventory(rows: List[Tuple[Any, ...]]) -> Dict[str, Any]:
    """Transform raw inventory rows into structured items and summary metrics."""
    items, low_stock, out_of_stock, categories = [], [], [], {}
    total_qty = total_reserved = 0
    for item_id, name, cat, qty, reserved, available in rows:
        total_qty += qty
        total_reserved += reserved
        if qty == 0:
            out_of_stock.append(name)
        elif qty < DEFAULT_CONFIG.low_stock_threshold:
            low_stock.append(name)
        categories[cat] = categories.get(cat, 0) + qty
        items.append(
            {
                "id": item_id,
                "name": name,
                "category": cat,
                "qty": qty,
                "reserved": reserved,
                "available": available,
            }
        )
    return {
        "items": items,
        "total_qty": total_qty,
        "total_reserved": total_reserved,
        "low_stock": low_stock,
        "out_of_stock": out_of_stock,
        "by_category": categories,
    }


def _save_report_backup(items: List[Dict[str, Any]], backup_dir: str) -> None:
    """Persist report snapshot to backup directory when explicitly requested."""
    os.makedirs(backup_dir, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(backup_dir, f"report_{stamp}.txt")
    with open(filepath, "w", encoding="utf-8") as handle:
        handle.write(str(items))


def get_inventory_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    repo: Optional[InventoryRepository] = None,
    write_backup: bool = False,
) -> Dict[str, Any]:
    """Orchestrate inventory report fetching, metric aggregation, and optional backup."""
    rows = (repo or get_repo()).fetch_report_rows(start_date, end_date, category)
    summary = _aggregate_inventory(rows)
    if write_backup:
        _save_report_backup(summary["items"], DEFAULT_CONFIG.backup_path)
    summary["generated_at"] = datetime.datetime.now().isoformat()
    summary["total_items"] = len(summary["items"])
    return summary


def update_stock(
    product_id: int, qty: int, reason: str = "", repo: Optional[InventoryRepository] = None
) -> bool:
    """Manually adjust stock level and record an audit log entry."""
    (repo or get_repo()).adjust_stock(product_id, qty, reason)
    return True


def sync_with_warehouse(config: InventoryConfig = DEFAULT_CONFIG) -> Dict[str, Any]:
    """Synchronize local inventory with external warehouse API via environment config."""
    if not config.warehouse_api_key:
        logger.info("Warehouse sync skipped: WAREHOUSE_API_KEY is not configured")
        return {"status": "skipped_no_credentials", "synced": 0}
    logger.info("Connecting to warehouse endpoint %s", config.warehouse_url)
    return {"status": "not_implemented", "synced": 0}